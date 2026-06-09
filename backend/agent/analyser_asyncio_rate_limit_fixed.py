"""
IAM Guardian - AI Analysis Agent (Parallel Edition)
Uses Async Claude to classify IAM policies as RED / AMBER / GREEN concurrently.
Includes exponential backoff to handle 429 Rate Limits (Tokens Per Minute).
"""

import json
import os
import asyncio
import random  # Required for adding jitter to backoff delays
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize the ASYNC client instead of the synchronous one
client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Lowered from 40 to 10 to protect your 30,000 Tokens Per Minute (ITPM) limit
MAX_CONCURRENT_REQUESTS = 10

SYSTEM_PROMPT = """You are a senior AWS cloud security expert specialising in IAM policy analysis.
Your job is to analyse AWS IAM policies and classify them by security risk.
Always respond with valid JSON only. No markdown, no explanation outside the JSON."""


def build_prompt(policy: dict) -> str:
    return f"""Analyse this AWS IAM policy and respond ONLY with a valid JSON object.

Policy details:
{json.dumps(policy, indent=2, default=str)}

Classification rules:
- RED   = Critical risk. Has wildcard Action (*) or Resource (*), dormant role unused for 90+ days 
          with broad permissions, or allows privilege escalation
- AMBER = Moderate risk. Broad service-level permissions (e.g. s3:* or ec2:*), unused for 30-90 days,
          missing MFA conditions on sensitive actions, overly permissive resource scope
- GREEN = Low risk. Scoped to specific resource ARNs, actively used within 30 days, 
          follows least-privilege principle

Respond with ONLY this JSON structure:
{{
  "classification": "RED",
  "justification": "Clear 2-3 sentence explanation of why this risk level was assigned",
  "risk_factors": [
    "Specific issue 1 found in this policy",
    "Specific issue 2 found in this policy"
  ],
  "suggested_policy": {{
    "Version": "2012-10-17",
    "Statement": [
      {{
        "Effect": "Allow",
        "Action": ["specific:action1", "specific:action2"],
        "Resource": "arn:aws:service:region:account:specific-resource"
      }}
    ]
  }}
}}"""


# Async function with a semaphore to control concurrency and backoff for 429 errors
async def analyse_policy(policy: dict, semaphore: asyncio.Semaphore, index: int, total: int) -> dict:
    async with semaphore:
        max_retries = 5
        base_delay = 2.0  # Initial sleep time in seconds if throttled

        for attempt in range(max_retries):
            try:
                print(f"  [{index}/{total}] Starting analysis: {policy.get('policy_name', 'unknown')} (Attempt {attempt + 1})")
                
                # Using 'await' for non-blocking API call
                message = await client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": build_prompt(policy)}],
                )

                raw = message.content[0].text.strip()

                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                result = json.loads(raw)
                result["original"] = policy
                print(f"  ✓ [{index}/{total}] Completed: {policy.get('policy_name')}")
                return result

            except anthropic.RateLimitError as e:
                # Catch 429 Token / Request Limit issues
                if attempt == max_retries - 1:
                    print(f"❌ Rate limit hit repeatedly. Giving up on: {policy.get('policy_name')}")
                    raise e  # Drop to general Exception block for fallback dict payload
                
                # Exponential backoff formula: (2^attempt * base_delay) + random jitter
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"⚠️ [429 Rate Limit] Token ceiling hit on '{policy.get('policy_name')}'. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error for policy {policy.get('policy_name')}: {e}")
                return {
                    "classification": "AMBER",
                    "justification": "Policy could not be automatically analysed. Manual review required.",
                    "risk_factors": ["Automated analysis failed — review manually"],
                    "suggested_policy": policy.get("document", {}),
                    "original": policy,
                }
            except Exception as e:
                print(f"❌ Analysis error for policy {policy.get('policy_name')}: {e}")
                return {
                    "classification": "AMBER",
                    "justification": f"Analysis error: {str(e)}. Manual review required.",
                    "risk_factors": ["Automated analysis error"],
                    "suggested_policy": policy.get("document", {}),
                    "original": policy,
                }


# Wrapper function to bundle tasks and execute them via event loop
def analyse_all_policies(policies: list) -> list:
    total = len(policies)
    print(f"Preparing parallel analysis for {total} policies (Max Concurrent: {MAX_CONCURRENT_REQUESTS})...")

    # Entry point for running async code from a synchronous environment
    return asyncio.run(_run_parallel_analysis(policies))


async def _run_parallel_analysis(policies: list) -> list:
    total = len(policies)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Create an async task for every policy
    tasks = [
        analyse_policy(policy, semaphore, i + 1, total) 
        for i, policy in enumerate(policies)
    ]
    
    # Fire them all off concurrently and wait for all to finish
    results = await asyncio.gather(*tasks)

    # Calculate Summary metrics
    red = sum(1 for r in results if r["classification"] == "RED")
    amber = sum(1 for r in results if r["classification"] == "AMBER")
    green = sum(1 for r in results if r["classification"] == "GREEN")
    print(f"\nAnalysis complete: {red} RED, {amber} AMBER, {green} GREEN")

    return results
