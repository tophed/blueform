import asyncio
from asyncio.subprocess import create_subprocess_exec
from sys import argv

import httpx
from bs4 import BeautifulSoup

RELEASE_URL = "https://releases.hashicorp.com"
TARGET = argv[1]


async def main():
    r = httpx.get(RELEASE_URL)
    soup = BeautifulSoup(r.text, "html.parser")

    async with asyncio.TaskGroup() as tg:
        for li in soup.find_all("li"):
            provider_href = li.a.get("href")
            if provider_href.startswith("/terraform-provider-"):
                tg.create_task(download_versions(provider_href))


async def download_versions(provider_href: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{RELEASE_URL}{provider_href}")
    soup = BeautifulSoup(r.text, "html.parser")
    async with asyncio.TaskGroup() as tg:
        count = 0
        limit = 1
        for li in soup.find_all("li"):
            version_href = li.a.get("href")
            if version_href.startswith("/terraform-provider-"):
                tg.create_task(download_version(version_href))
                count += 1
                if count == limit:
                    break


async def download_version(version_href: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{RELEASE_URL}{version_href}")
    soup = BeautifulSoup(r.text, "html.parser")
    for li in soup.find_all("li"):
        download_url = li.a.get("href")
        # https://releases.hashicorp.com/terraform-provider-google/4.71.0/terraform-provider-google_4.71.0_darwin_arm64.zip
        if TARGET in download_url:
            type_ = download_url.split("/")[-3].replace("terraform-provider-", "")
            prefix = f"bin/{TARGET}/providers/registry.terraform.io/hashicorp/{type_}"
            process = await create_subprocess_exec('wget', '-P', prefix, download_url)
            await process.wait()


if __name__ == "__main__":
    asyncio.run(main())
