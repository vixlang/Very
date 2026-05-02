from .base import Command
import argparse
from .utils import log, console, Config
import urllib.request
import json
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import time


class SearchCmd(Command):
    NAME = "search"
    
    # 缓存配置
    CACHE_DIR = Config.VIX_HOME / "cache"
    CACHE_FILE = CACHE_DIR / "search_cache.json"
    CACHE_EXPIRY = 3600  # 缓存过期时间：1小时（秒）
    
    # 重试配置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试间隔（秒）

    def execute(self):
        keyword = getattr(self.namespace, "keyword", "")
        no_cache = getattr(self.namespace, "no_cache", False)
        clear_cache = getattr(self.namespace, "clear_cache", False)
        cache_status = getattr(self.namespace, "cache_status", False)
        
        # 处理缓存清理命令
        if clear_cache:
            self.clear_cache()
            return
        
        # 处理缓存状态查询
        if cache_status:
            self.show_cache_status()
            return
        
        log.section(f"搜索包: {keyword if keyword else '全部'}")
        
        try:
            if no_cache:
                log.info("正在从 GitHub 获取包列表...（不使用缓存）")
                packages = self.fetch_with_retry()
                # 即使使用 --no-cache，也更新缓存
                self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                self.save_cache(packages)
            else:
                packages = self.fetch_packages_with_cache()
            
            if not packages:
                log.warning("未找到任何包")
                return
            
            # 过滤结果
            if keyword:
                filtered = [
                    p for p in packages 
                    if keyword.lower() in p['name'].lower() 
                    or keyword.lower() in p.get('description', '').lower()
                ]
            else:
                filtered = packages
            
            if not filtered:
                log.warning(f"未找到包含 '{keyword}' 的包")
                return
            
            self.display_results(filtered)
            
        except Exception as e:
            log.error(
                f"搜索失败\n\n[white]{str(e)}[/white]\n\n"
                "[yellow]请检查:[/yellow]\n  • 网络连接是否正常\n  • GitHub API 是否可访问"
            )
            return

    def fetch_with_retry(self):
        """带重试机制的 API 调用"""
        last_exception = None
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    log.info(f"重试第 {attempt - 1} 次...")
                    time.sleep(self.RETRY_DELAY)
                
                return self.fetch_github_packages()
                
            except urllib.error.HTTPError as e:
                last_exception = e
                
                if e.code == 403:
                    # 速率限制，需要等待更长时间
                    if attempt < self.MAX_RETRIES:
                        wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))  # 指数退避
                        log.warning(f"GitHub API 速率限制，{wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("GitHub API 速率限制已用完，请稍后再试（建议等待几分钟后重试）")
                
                elif e.code == 404:
                    raise Exception("GitHub API 端点不存在，请检查网络连接")
                
                elif e.code >= 500:
                    # 服务器错误，可以重试
                    if attempt < self.MAX_RETRIES:
                        log.warning(f"服务器错误 ({e.code})，将重试...")
                        continue
                    else:
                        raise Exception(f"GitHub API 服务器错误 ({e.code})，请稍后重试")
                
                else:
                    raise Exception(f"HTTP 错误: {e.code} {e.reason}")
                    
            except urllib.error.URLError as e:
                last_exception = e
                
                if attempt < self.MAX_RETRIES:
                    log.warning(f"网络错误: {e.reason}，将重试...")
                    continue
                else:
                    raise Exception(f"网络错误: {e.reason}，请检查网络连接")
                    
            except Exception as e:
                # 其他未知错误，不重试
                raise Exception(f"请求失败: {str(e)}")
        
        # 所有重试都失败
        if last_exception:
            raise Exception(f"经过 {self.MAX_RETRIES} 次重试后仍然失败: {str(last_exception)}")

    def fetch_packages_with_cache(self):
        """使用缓存获取包列表"""
        # 确保缓存目录存在
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 尝试从缓存读取
        cached_data = self.read_cache()
        if cached_data:
            log.info("使用缓存数据")
            return cached_data
        
        # 缓存不存在或已过期，从 API 获取（带重试）
        log.info("正在从 GitHub 获取包列表...")
        packages = self.fetch_with_retry()
        
        # 保存到缓存
        self.save_cache(packages)
        
        return packages

    def read_cache(self):
        """读取缓存文件"""
        if not self.CACHE_FILE.exists():
            return None
        
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # 检查缓存是否过期
            if time.time() - cache_data['timestamp'] > self.CACHE_EXPIRY:
                log.debug("缓存已过期")
                return None
            
            return cache_data['packages']
        except (json.JSONDecodeError, KeyError) as e:
            log.debug(f"缓存文件损坏: {e}")
            return None
        except Exception as e:
            log.debug(f"读取缓存失败: {e}")
            return None

    def save_cache(self, packages):
        """保存数据到缓存"""
        try:
            cache_data = {
                'timestamp': time.time(),
                'packages': packages
            }
            
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            log.debug(f"缓存已保存: {self.CACHE_FILE}")
        except Exception as e:
            log.debug(f"保存缓存失败: {e}")

    def fetch_github_packages(self):
        """从 GitHub API 获取 vixlang 组织下的所有仓库（支持分页）"""
        packages = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/orgs/vixlang/repos?per_page={per_page}&page={page}&type=sources"
            
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Vpm-Package-Manager'
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                # 如果没有数据，说明已经到最后一页
                if not data:
                    break
                
                # 过滤出 vix 包（通常以 vlib- 开头）
                for repo in data:
                    if repo['name'].startswith('vlib-') or repo['name'] == 'vpm':
                        packages.append({
                            'name': repo['name'],
                            'description': repo['description'] or '无描述',
                            'stars': repo['stargazers_count'],
                            'language': repo['language'] or 'Unknown',
                            'updated': repo['updated_at'][:10],
                            'url': repo['html_url']
                        })
                
                # 如果返回的数据少于 per_page，说明已经是最后一页
                if len(data) < per_page:
                    break
                
                page += 1
        
        # 按星标数降序排序
        packages.sort(key=lambda x: x['stars'], reverse=True)
        
        return packages

    def display_results(self, packages):
        """显示搜索结果"""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("包名", style="green", width=25)
        table.add_column("描述", style="white", width=50)
        table.add_column("星标", justify="right", style="yellow", width=6)
        table.add_column("语言", style="magenta", width=12)
        table.add_column("更新时间", style="dim", width=12)
        
        for pkg in packages:
            # 简化包名显示（去掉 vlib- 前缀）
            short_name = pkg['name'].replace('vlib-', '', 1) if pkg['name'].startswith('vlib-') else pkg['name']
            
            table.add_row(
                short_name,
                pkg['description'][:47] + "..." if len(pkg['description']) > 50 else pkg['description'],
                str(pkg['stars']),
                pkg['language'],
                pkg['updated']
            )
        
        console.print()
        console.print(table)
        console.print()
        
        # 显示统计信息
        log.success(f"共找到 {len(packages)} 个包")
        console.print()
        console.print(
            Panel(
                "[dim]使用 [white]vpm add <包名>[/white] 安装包\n"
                "例如: [green]vpm add vnet[/green] 或 [green]vpm add vixlang/vlib-vnet[/green][/dim]",
                title="[bold]💡 提示[/bold]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print()

    def clear_cache(self):
        """清理缓存文件"""
        log.section("清理缓存")
        
        if not self.CACHE_FILE.exists():
            log.info("缓存文件不存在，无需清理")
            return
        
        try:
            # 获取缓存文件大小
            cache_size = self.CACHE_FILE.stat().st_size
            cache_size_kb = cache_size / 1024
            
            # 删除缓存文件
            self.CACHE_FILE.unlink()
            
            log.success(f"缓存已清理")
            log.info(f"释放空间: {cache_size_kb:.2f} KB")
            
        except Exception as e:
            log.error(f"清理缓存失败: {e}")

    def show_cache_status(self):
        """显示缓存状态"""
        log.section("缓存状态")
        
        if not self.CACHE_FILE.exists():
            log.info("缓存文件不存在")
            log.info("运行 [green]vpm search[/green] 将自动创建缓存")
            return
        
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            timestamp = cache_data['timestamp']
            packages_count = len(cache_data['packages'])
            cache_age = time.time() - timestamp
            cache_size = self.CACHE_FILE.stat().st_size
            cache_size_kb = cache_size / 1024
            
            # 计算过期时间
            remaining_time = self.CACHE_EXPIRY - cache_age
            if remaining_time > 0:
                remaining_minutes = int(remaining_time / 60)
                status = f"[green]有效[/green]（剩余 {remaining_minutes} 分钟）"
            else:
                status = "[red]已过期[/red]"
            
            # 格式化时间
            from datetime import datetime
            cache_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            console.print()
            console.print(f"缓存文件: [cyan]{self.CACHE_FILE}[/cyan]")
            console.print(f"创建时间: [white]{cache_time}[/white]")
            console.print(f"缓存大小: [yellow]{cache_size_kb:.2f} KB[/yellow]")
            console.print(f"包数量: [magenta]{packages_count}[/magenta]")
            console.print(f"状态: {status}")
            console.print()
            
        except Exception as e:
            log.error(f"读取缓存状态失败: {e}")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        search_parser = p.add_parser(
            "search",
            help="搜索可用的包",
            description="从 GitHub vixlang 组织中搜索可用的 vix 包",
        )
        search_parser.add_argument(
            "keyword",
            nargs="?",
            default="",
            help="搜索关键词（可选），留空显示所有包"
        )
        search_parser.add_argument(
            "--no-cache",
            action="store_true",
            help="不使用缓存，强制从 GitHub 获取最新数据"
        )
        search_parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="清理本地缓存文件"
        )
        search_parser.add_argument(
            "--cache-status",
            action="store_true",
            help="查看缓存状态信息"
        )
        return search_parser
