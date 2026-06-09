"""
IAM Guardian - AI Analysis Agent (Paced Parallel Edition)
Uses Async Claude to classify IAM policies concurrently but staggers execution
to completely eliminate instant 429 Token Per Minute spikes.
"""

import json
import os
import asyncio
import random
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Drop concurrency down to 3 to safely live inside your tight 30k token tier
MAX_CONCURRENT_REQUESTS = 3

SYSTEM_PROMPT = """You are a senior AWS cloud security expert specialising in IAM policy analysis.
Your job is to analyse AWS IAM policies and classify them by security risk.
You must respond with a single, strictly valid JSON object following the requested schema."""


def build_prompt(policy: dict) -> str:
    return f"""Analyse this AWS IAM policy.

Policy details:
{json.dumps(policy, indent=2, default=str)}

Classification rules:
- RED   = Critical risk. Has wildcard Action (*) or Resource (*), dormant role unused for 90+ days 
          with broad permissions, or allows privilege escalation
- AMBER = Moderate risk. Broad service-level permissions (e.g. s3:* or ec2:*), unused for 30-90 days,
          missing MFA conditions on sensitive actions, overly permissive resource scope
- GREEN = Low risk. Scoped to specific resource ARNs, actively used within 30 days, 
          follows least-privilege principle

Provide your analysis in this exact JSON schema:
{{
  "classification": "RED" | "AMBER" | "GREEN",
  "justification": "Clear 2-3 sentence explanation of why this risk level was assigned",
  "risk_factors": ["string"],
  "suggested_policy": {{
    "Version": "2012-10-17",
    "Statement": [
      {{
        "Effect": "Allow" | "Deny",
        "Action": ["string"],
        "Resource": "string"
      }}
    ]
  }}
}}"""


async def analyse_policy(policy: dict, semaphore: asyncio.Semaphore, index: int, total: int) -> dict:
    # CRITICAL FIX 1: Stagger the start times slightly so they don't hit the API at the exact same millisecond
    # This prevents the initial batch from instantly breaking the token bucket
    await asyncio.sleep(index * 0.75)

    async with semaphore:
        max_retries = 5
        base_delay = 4.0  # Increased to give the 1-minute token window plenty of room to clear

        for attempt in range(max_retries):
            try:
                print(f"  [{index}/{total}] Starting analysis: {policy.get('policy_name', 'unknown')} (Attempt {attempt + 1})")
                
                message = await client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=2500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": build_prompt(policy)}],
                )

                raw = message.content[0].text.strip()

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
                if attempt == max_retries - 1:
                    print(f"❌ Rate limit hit repeatedly. Falling back to safe response for: {policy.get('policy_name')}")
                    return {
                        "classification": "AMBER",
                        "justification": "Policy hit Anthropic rate limits (TPM ceiling) repeatedly during scanning queue.",
                        "risk_factors": ["Rate limit exhausted — check back later or upgrade Tier"],
                        "suggested_policy": policy.get("document", {}),
                        "original": policy,
                    }
                # Double the delay each time + add random jitter
                delay = (base_delay * (2 ** attempt)) + random.uniform(1, 3)
                print(f"⚠️ [429 Rate Limit] Token ceiling hit on '{policy.get('policy_name')}'. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

            except anthropic.APIConnectionError as e:
                if attempt == max_retries - 1:
                    print(f"❌ Connection error persisted. Giving up on: {policy.get('policy_name')}")
                    return {
                        "classification": "AMBER",
                        "justification": "Network connection dropped persistently during analysis.",
                        "risk_factors": ["Network connection timeout"],
                        "suggested_policy": policy.get("document", {}),
                        "original": policy,
                    }
                delay = (base_delay * (2 ** attempt)) + random.uniform(1, 2)
                print(f"⚠️ [Connection Error] Network dropped for '{policy.get('policy_name')}'. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error for policy {policy.get('policy_name')}: {e}")
                return {
                    "classification": "AMBER",
                    "justification": "Policy analysis returned malformed JSON structure from AI.",
                    "risk_factors": ["Automated JSON parsing failed — review manually"],
                    "suggested_policy": policy.get("document", {}),
                    "original": policy,
                }
            except Exception as e:
                print(f"❌ Permanent failure for policy {policy.get('policy_name')}: {e}")
                return {
                    "classification": "AMBER",
                    "justification": f"Analysis error: {str(e)}. Manual review required.",
                    "risk_factors": ["Automated analysis error"],
                    "suggested_policy": policy.get("document", {}),
                    "original": policy,
                }


def analyse_all_policies(policies: list) -> list:
    total = len(policies)
    print(f"Preparing parallel analysis for {total} policies (Max Concurrent: {MAX_CONCURRENT_REQUESTS})...")
    return asyncio.run(_run_parallel_analysis(policies))


async def _run_parallel_analysis(policies: list) -> list:
    total = len(policies)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    tasks = [
        analyse_policy(policy, semaphore, i + 1, total) 
        for i, policy in enumerate(policies)
    ]
    
    # CRITICAL FIX 2: Safeguard gather processing against absolute failure
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for i, r in enumerate(raw_results):
        if isinstance(r, Exception):
            print(f"❌ Exception bypassed to collection array: {r}")
            fallback = {
                "classification": "AMBER",
                "justification": f"Critical unhandled engine exception: {str(r)}",
                "risk_factors": ["Unhandled exceptions during async gathering pipeline"],
                "suggested_policy": policies[i].get("document", {}),
                "original": policies[i]
            }
            results.append(fallback)
        else:
            results.append(r)

    red = sum(1 for r in results if r.get("classification") == "RED")
    amber = sum(1 for r in results if r.get("classification") == "AMBER")
    green = sum(1 for r in results if r.get("classification") == "GREEN")
    print(f"\nAnalysis complete: {red} RED, {amber} AMBER, {green} GREEN")

    return results
