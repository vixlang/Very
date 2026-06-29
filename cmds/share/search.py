import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..utils import DEFAULT_ORG


def _read_cache(cache_file: Path, expiry: int = 3600):
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["timestamp"] > expiry:
            return None
        return data["packages"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(cache_dir: Path, cache_file: Path, packages):
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        data = {"timestamp": time.time(), "packages": packages}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _clear_cache(cache_file: Path):
    if cache_file.exists():
        cache_file.unlink()


def _fetch_github_packages(prefix: str, include_extra: str | None = None):
    packages = []
    page = 1
    per_page = 100
    ctx = ssl.create_default_context()

    while True:
        url = (
            f"https://api.github.com/orgs/{DEFAULT_ORG}"
            f"/repos?per_page={per_page}&page={page}&type=sources"
        )
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Very-Project-Manager",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data:
                break
            for repo in data:
                if repo["name"].startswith(prefix) or (
                    include_extra and repo["name"] == include_extra
                ):
                    packages.append(
                        {
                            "name": repo["name"],
                            "description": repo["description"] or "无描述",
                            "stars": repo["stargazers_count"],
                            "language": repo["language"] or "Unknown",
                            "updated": repo["updated_at"][:10],
                            "url": repo["html_url"],
                        }
                    )
            if len(data) < per_page:
                break
            page += 1

    packages.sort(key=lambda x: x["stars"], reverse=True)
    return packages


def _fetch_with_retry(fetch_fn, max_retries=3, retry_delay=2):
    from rich.live import Live
    from rich.spinner import Spinner

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                time.sleep(retry_delay)
            with Live(
                Spinner("dots", text="正在从 GitHub 获取数据..."),
                refresh_per_second=10,
                transient=True,
            ):
                result = fetch_fn()
            return result
        except urllib.error.HTTPError as e:
            last_exception = e
            if e.code == 403:
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    time.sleep(wait_time)
                    continue
                raise Exception("GitHub API 速率限制已用完，请稍后再试")
            elif e.code == 404:
                raise Exception("GitHub API 端点不存在")
            elif e.code >= 500:
                if attempt < max_retries:
                    continue
                raise Exception(f"GitHub API 服务器错误 ({e.code})")
            else:
                raise Exception(f"HTTP 错误: {e.code}")
        except urllib.error.URLError as e:
            last_exception = e
            if attempt < max_retries:
                continue
            raise Exception("网络错误，请检查网络连接")
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")

    if last_exception:
        raise Exception(f"经过 {max_retries} 次重试后仍然失败")


def _sort_packages(packages, sort_by):
    if sort_by == "stars":
        return sorted(packages, key=lambda x: x["stars"], reverse=True)
    elif sort_by == "updated":
        return sorted(packages, key=lambda x: x["updated"], reverse=True)
    elif sort_by == "name":
        return sorted(packages, key=lambda x: x["name"].lower())
    return sorted(packages, key=lambda x: x["stars"], reverse=True)
