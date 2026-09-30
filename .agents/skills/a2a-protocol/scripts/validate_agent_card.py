"""
A2A AgentCard Validator.

Fetches and validates an A2A AgentCard from a given URL,
verifying it meets the minimum A2A v1.0 protocol requirements.

Usage:
    python scripts/validate_agent_card.py --url http://localhost:8001
    python scripts/validate_agent_card.py --url http://localhost:8001 --verbose
"""
from __future__ import annotations

import asyncio
import logging
import sys

import click
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["name", "description", "url", "version", "capabilities", "skills", "defaultInputModes", "defaultOutputModes"]
VALID_INPUT_MODES = {"text", "data", "file"}
VALID_OUTPUT_MODES = {"text", "data", "file"}
VALID_AUTH_SCHEMES = {"Bearer", "ApiKey", "None", "basic"}


def validate_card(card: dict) -> list[str]:
    """Validate AgentCard fields. Returns a list of error strings (empty = valid)."""
    errors: list[str] = []

    # Required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in card:
            errors.append(f"Missing required field: '{field}'")

    # Skills must be non-empty list
    skills = card.get("skills", [])
    if not isinstance(skills, list) or len(skills) == 0:
        errors.append("'skills' must be a non-empty list")
    else:
        for i, skill in enumerate(skills):
            if not skill.get("id"):
                errors.append(f"Skill[{i}] missing 'id'")
            if not skill.get("name"):
                errors.append(f"Skill[{i}] missing 'name'")
            if not skill.get("description"):
                errors.append(f"Skill[{i}] missing 'description'")

    # Capabilities
    caps = card.get("capabilities", {})
    if "streaming" not in caps:
        errors.append("'capabilities.streaming' is missing")
    if "pushNotifications" not in caps:
        errors.append("'capabilities.pushNotifications' is missing")

    # Input/output modes
    input_modes = set(card.get("defaultInputModes", []))
    if not input_modes.issubset(VALID_INPUT_MODES):
        errors.append(f"Invalid defaultInputModes: {input_modes - VALID_INPUT_MODES}")

    output_modes = set(card.get("defaultOutputModes", []))
    if not output_modes.issubset(VALID_OUTPUT_MODES):
        errors.append(f"Invalid defaultOutputModes: {output_modes - VALID_OUTPUT_MODES}")

    # Authentication
    auth = card.get("authentication")
    if auth is not None:
        schemes = set(auth.get("schemes", []))
        invalid_schemes = schemes - VALID_AUTH_SCHEMES
        if invalid_schemes:
            errors.append(f"Unknown authentication schemes: {invalid_schemes}")

    # URL must be a string
    url = card.get("url", "")
    if not isinstance(url, str) or not url.startswith("http"):
        errors.append(f"'url' must be an HTTP/HTTPS URL, got: {url!r}")

    return errors


async def fetch_and_validate(agent_url: str, verbose: bool) -> bool:
    """Fetch the AgentCard and validate it. Returns True if valid."""
    well_known_url = agent_url.rstrip("/") + "/.well-known/agent.json"
    logger.info("Fetching AgentCard from: %s", well_known_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(well_known_url)
    except httpx.ConnectError as exc:
        logger.error("Cannot connect to agent at %s: %s", agent_url, exc)
        return False
    except httpx.TimeoutException:
        logger.error("Connection timed out when fetching AgentCard from %s", well_known_url)
        return False

    if response.status_code != 200:
        logger.error("AgentCard endpoint returned HTTP %d (expected 200)", response.status_code)
        return False

    try:
        card = response.json()
    except Exception as exc:
        logger.error("AgentCard response is not valid JSON: %s", exc)
        return False

    if verbose:
        import json
        print("\nAgentCard JSON:")
        print(json.dumps(card, indent=2))
        print()

    errors = validate_card(card)

    if errors:
        logger.error("AgentCard validation FAILED with %d error(s):", len(errors))
        for err in errors:
            logger.error("  - %s", err)
        return False

    # Summary
    logger.info("AgentCard validation PASSED.")
    logger.info("  Agent Name   : %s", card.get("name"))
    logger.info("  Version      : %s", card.get("version"))
    logger.info("  Streaming    : %s", card.get("capabilities", {}).get("streaming"))
    logger.info("  Skills       : %d declared", len(card.get("skills", [])))
    for skill in card.get("skills", []):
        logger.info("    - [%s] %s", skill.get("id"), skill.get("name"))
    return True


@click.command()
@click.option("--url", required=True, help="Base URL of the A2A agent (e.g. http://localhost:8001).")
@click.option("--verbose", is_flag=True, default=False, help="Print full AgentCard JSON.")
def main(url: str, verbose: bool) -> None:
    """Validate an A2A AgentCard served at /.well-known/agent.json."""
    is_valid = asyncio.run(fetch_and_validate(agent_url=url, verbose=verbose))
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
