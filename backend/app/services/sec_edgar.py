from __future__ import annotations
import logging
import httpx

log = logging.getLogger("service.sec_edgar")

SEC_SUBMISSIONS = "https://data.sec.gov/submissions"

async def fetch_company_submissions(clk10: str, user_agent: str) -> dict:
    """
    Minimal SEC JSON fetch.
    Compliance Note: The SEC requires a declared User-Agent header (email address) 
    for automated access. Failing to provide this will result in a 403 Forbidden.
    """

    # Now, we pad the CIK to 10 digits as required by the SEC URL structure.
    clk10 = clk10.zfill(10)
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    url = f"{SEC_SUBMISSIONS}/CIK{clk10}.json"

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()