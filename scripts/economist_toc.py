#!/usr/bin/env python3
"""
经济学人目录自动提取脚本
从 PDF 末尾的 Table of Contents 页面提取完整目录
"""

import os
import sys
import subprocess
import urllib.parse
import urllib.request
import json
import fitz  # PyMuPDF
from datetime import datetime

REPO_DIR = "/workspaces/awesome-english-ebooks"
TELEGRAM_CHAT_ID = "1268358344"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# 缓存翻译结果，避免重复调用 API
translation_cache = {}

def translate_with_kimi(title):
    """使用 Kimi API 翻译标题"""
    if title in translation_cache:
        return translation_cache[title]
    
    # 简单的短语直接翻译
    simple_translations = {
        "Politics": "政治",
        "Business": "商业",
        "The weekly cartoon": "本周漫画",
    }
    if title in simple_translations:
        return simple_translations[title]
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {KIMI_API_KEY}"
        }
        
        data = {
            "model": "moonshot-v1-8k",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的翻译助手。请将给定的经济学人文章标题翻译成简洁准确的中文，只返回翻译结果，不要解释。"
                },
                {
                    "role": "user",
                    "content": f"请翻译以下标题：{title}"
                }
            ],
            "temperature": 0.3
        }
        
        req = urllib.request.Request(
            KIMI_API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            translation = result['choices'][0]['message']['content'].strip()
            # 清理可能的引号
            translation = translation.strip('"「」『』')
            translation_cache[title] = translation
            return translation
            
    except Exception as e:
        print(f"  ⚠️ 翻译失败: {title[:30]}... - {e}")
        return "[待译]"

def run(cmd):
    """执行 shell 命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def get_latest_economist():
    """获取最新经济学人 PDF 路径"""
    economist_dir = os.path.join(REPO_DIR, "01_economist")
    if not os.path.exists(economist_dir):
        return None
    
    dirs = [d for d in os.listdir(economist_dir) if d.startswith("te_")]
    if not dirs:
        return None
    
    dirs.sort(reverse=True)
    latest_dir = dirs[0]
    
    pdf_path = os.path.join(economist_dir, latest_dir, f"TheEconomist.{latest_dir[3:]}.pdf")
    return pdf_path if os.path.exists(pdf_path) else None

def extract_toc_from_pdf(pdf_path):
    """
    从 PDF 末尾的 Table of Contents 页面提取目录结构
    结合 PDF 大纲获取页码信息
    """
    sections_config = [
        ('The world this week', '本周世界'),
        ('Leaders', '社论'),
        ('Letters', '读者来信'),
        ('Briefing', '深度报道'),
        ('United States', '美国'),
        ('The Americas', '美洲'),
        ('Asia', '亚洲'),
        ('China', '中国'),
        ('Middle East & Africa', '中东与非洲'),
        ('Europe', '欧洲'),
        ('Britain', '英国'),
        ('International', '国际'),
        ('Essay', '随笔'),
        ('Business', '商业'),
        ('Finance & economics', '财经'),
        ('Science & technology', '科技'),
        ('Culture', '文化'),
        ('Economic & financial indicators', '经济指标'),
        ('Obituary', '讣告'),
    ]
    
    section_names = [s[0] for s in sections_config]
    section_cn_map = {s[0]: s[1] for s in sections_config}
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # 1. 从 PDF 大纲获取文章列表和页码
    toc = doc.get_toc()
    articles_with_pages = {}  # {title_lower: (title, page)}
    article_keys = []  # [(title_lower, title, page), ...] 用于模糊匹配
    
    for level, title, page in toc:
        if len(title) > 3:
            # 存储标题的小写版本用于匹配
            key = title.lower()
            articles_with_pages[key] = (title, page)
            article_keys.append((key, title, page))
    
    # 2. 从最后几页读取 Table of Contents 文本
    toc_lines = []
    # 读取最后 10 页（目录通常在末尾）
    for page_num in range(max(0, total_pages - 10), total_pages):
        page = doc[page_num]
        text = page.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        toc_lines.extend(lines)
    
    doc.close()
    
    # 3. 解析目录结构
    sections_data = []
    current_section = None
    current_articles = []
    
    # 找到 "Table of Contents" 开始的位置
    toc_started = False
    pending_line = None  # 用于处理跨行标题
    
    for i, line in enumerate(toc_lines):
        # 标记目录开始
        if line == "Table of Contents":
            toc_started = True
            continue
        
        if not toc_started:
            continue
        
        # 检查是否是板块标题
        if line in section_names:
            # 特殊处理：根据页码判断是否是真正的板块标题
            # The world this week 的子板块页码都在 15 页以内
            line_lower = line.lower()
            is_early_page = False
            if line_lower in articles_with_pages:
                _, page = articles_with_pages[line_lower]
                is_early_page = page < 20  # 前 20 页的是子板块
            
            # 如果当前是 The world this week 且页码较小，则是子板块
            if current_section == 'The world this week' and is_early_page:
                # 作为文章添加，不切换板块
                pass  # 继续执行下面的文章匹配逻辑
            else:
                # 保存之前的板块
                if current_section and current_articles:
                    sections_data.append((
                        current_section,
                        section_cn_map.get(current_section, current_section),
                        current_articles
                    ))
                    print(f"  ✓ {current_section}: {len(current_articles)} 篇文章")
                
                current_section = line
                current_articles = []
                pending_line = None
                continue
        
        # 跳过分隔线
        if not line or len(line) < 5:
            pending_line = None
            continue
        
        # 处理 The world this week 的子板块（它们是实际的内容页）
        if line in ['Politics', 'Business', 'The weekly cartoon']:
            if current_section == 'The world this week':
                # 查找该子板块的页码
                line_lower = line.lower()
                if line_lower in articles_with_pages:
                    title, page = articles_with_pages[line_lower]
                    current_articles.append((title, page))
            pending_line = None
            continue
        
        # 处理跨行标题：如果上一行以逗号结尾，合并当前行
        if pending_line:
            combined = pending_line + " " + line
            combined_lower = combined.lower()
            if combined_lower in articles_with_pages:
                title, page = articles_with_pages[combined_lower]
                current_articles.append((title, page))
                pending_line = None
                continue
            # 合并后仍不匹配，尝试只用当前行
            pending_line = None
        
        # 检查是否是作者续行（以 "writes " 开头）
        if line.startswith('writes '):
            # 这是上一行的续行，跳过
            continue
        
        # 尝试匹配文章标题
        line_lower = line.lower()
        matched = False
        
        # 1. 精确匹配
        if line_lower in articles_with_pages:
            title, page = articles_with_pages[line_lower]
            current_articles.append((title, page))
            matched = True
        else:
            # 2. 尝试去除 "writes" 部分匹配
            clean_line = line.split(', writes')[0].strip()
            clean_line_lower = clean_line.lower()
            if clean_line_lower in articles_with_pages:
                title, page = articles_with_pages[clean_line_lower]
                current_articles.append((title, page))
                matched = True
            else:
                # 3. 模糊匹配：查找以当前行开头的 TOC 标题
                # 处理 PDF 文本提取截断的情况
                for key, toc_title, toc_page in article_keys:
                    # 检查是否互相是对方的前缀（处理截断）
                    if key.startswith(line_lower) or line_lower.startswith(key[:50]):
                        current_articles.append((toc_title, toc_page))
                        matched = True
                        break
        
        if matched:
            pending_line = None
        elif line.endswith(','):
            # 可能是跨行标题的开始，保存等待下一行
            pending_line = line
        else:
            pending_line = None
    
    # 保存最后一个板块
    if current_section and current_articles:
        sections_data.append((
            current_section,
            section_cn_map.get(current_section, current_section),
            current_articles
        ))
        print(f"  ✓ {current_section}: {len(current_articles)} 篇文章")
    
    return sections_data

def translate_title(title):
    """
    翻译文章标题为中文
    使用 Kimi API 进行翻译
    """
    # 常见短语的直接映射（避免 API 调用）
    translations = {
        "Politics": "政治",
        "Business": "商业",
        "The weekly cartoon": "本周漫画",
    }
    
    if title in translations:
        return translations[title]
    
    # 使用 Kimi API 翻译
    return translate_with_kimi(title)

def batch_translate_titles(titles):
    """批量翻译标题，减少 API 调用次数 - 分批处理"""
    if not titles:
        return {}
    
    # 检查缓存
    cached = {}
    to_translate = []
    for title in titles:
        if title in translation_cache:
            cached[title] = translation_cache[title]
        else:
            to_translate.append(title)
    
    if not to_translate:
        return cached
    
    # 分批翻译，每批 5 个标题
    batch_size = 5
    total = len(to_translate)
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = to_translate[batch_start:batch_end]
        
        print(f"  翻译批次 {batch_start//batch_size + 1}/{(total-1)//batch_size + 1} ({batch_start+1}-{batch_end}/{total})...", end=" ", flush=True)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {KIMI_API_KEY}"
            }
            
            # 构建批量翻译提示
            titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(batch)])
            
            data = {
                "model": "moonshot-v1-8k",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的翻译助手。请将以下经济学人文章标题翻译成简洁准确的中文。保持原有编号顺序，每行只返回翻译结果，格式：1. [翻译]\n2. [翻译]"
                    },
                    {
                        "role": "user",
                        "content": f"请翻译以下标题：\n{titles_text}"
                    }
                ],
                "temperature": 0.3
            }
            
            req = urllib.request.Request(
                KIMI_API_URL,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                translation = result['choices'][0]['message']['content'].strip()
                
                # 解析批量翻译结果
                for i, title in enumerate(batch):
                    # 查找对应编号的翻译
                    found = False
                    for line in translation.split('\n'):
                        line_stripped = line.strip()
                        if line_stripped.startswith(f"{i+1}.") or line_stripped.startswith(f"{i+1}、"):
                            # 找到分隔符后的内容
                            for sep in ['. ', '、', '.', ' ']:
                                if sep in line_stripped[2:]:
                                    cn_title = line_stripped.split(sep, 1)[1].strip()
                                    break
                            else:
                                cn_title = line_stripped[2:].strip()
                            cn_title = cn_title.strip('"「」『』')
                            if cn_title:
                                translation_cache[title] = cn_title
                                cached[title] = cn_title
                                found = True
                                break
                    
                    if not found:
                        # 如果没找到对应行，使用单条翻译
                        cached[title] = translate_with_kimi(title)
                
                print("✓")
                        
        except Exception as e:
            print(f"✗ ({e})")
            # 失败时逐个翻译
            for title in batch:
                cached[title] = translate_with_kimi(title)
    
    return cached

def format_toc(sections_data, pdf_path):
    """格式化目录为 Markdown 格式，带可点击链接和中英对照"""
    date_str = "Unknown"
    parts = pdf_path.split('/')
    for part in parts:
        if part.startswith('te_'):
            date_str = part[3:].replace('.', '/')
            break
    
    # 收集所有需要翻译的标题
    all_titles = []
    for sec_en, sec_cn, articles in sections_data:
        for title, page in articles:
            if title not in {"Politics", "Business", "The weekly cartoon"}:
                all_titles.append(title)
    
    # 批量翻译
    print(f"🌐 正在翻译 {len(all_titles)} 个标题...")
    translations = batch_translate_titles(all_titles)
    print(f"✅ 翻译完成")
    
    lines = [f"📰 *The Economist | 经济学人* - {date_str}\n"]
    lines.append("─" * 50 + "\n")
    
    # 添加使用说明
    lines.append("💡 *使用说明*")
    lines.append("• 点击英文标题可在 Google 搜索原文")
    lines.append("• 运行以下命令查看文章内容：")
    lines.append(f"  `python3 scripts/economist_article.py \"文章标题\"`")
    lines.append("")
    
    total_articles = 0
    for sec_en, sec_cn, articles in sections_data:
        total_articles += len(articles)
        # 板块标题加粗，英中对照
        lines.append(f"\n📂 *{sec_en}* ｜ {sec_cn}")
        
        for title, page in articles:
            # 获取翻译
            cn_title = translations.get(title, "[待译]")
            
            # 构建搜索链接
            search_query = urllib.parse.quote(f"{title} site:economist.com")
            search_url = f"https://www.google.com/search?q={search_query}"
            
            # 格式：英文标题(中文翻译) + 页码
            lines.append(f"• [{title}]({search_url}) _{cn_title}_ ｜ p.{page}")
        
        lines.append("")
    
    lines.append("─" * 50)
    lines.append(f"\n_总计: {len(sections_data)} 个板块, {total_articles} 篇文章_")
    
    return "\n".join(lines)

def save_to_file(message, pdf_path):
    """保存到文件"""
    date_str = "unknown"
    parts = pdf_path.split('/')
    for part in parts:
        if part.startswith('te_'):
            date_str = part[3:]
            break
    
    output_path = f"/home/codespace/.openclaw/workspace/economist_toc_{date_str}.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(message)
    print(f"💾 目录已保存到: {output_path}")
    return output_path

def extract_all_articles_content(pdf_path, sections_data):
    """
    提取所有文章的完整内容
    返回一个包含所有文章内容的字符串
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
    # 构建标题到页码的映射
    title_to_page = {}
    for level, title, page in toc:
        if len(title) > 3:
            title_to_page[title.lower()] = (title, page)
    
    lines = []
    lines.append("📚 THE ECONOMIST - FULL CONTENT INDEX")
    lines.append("=" * 60)
    lines.append("")
    
    for sec_en, sec_cn, articles in sections_data:
        lines.append(f"\n{'='*60}")
        lines.append(f"📂 {sec_en} | {sec_cn}")
        lines.append("=" * 60)
        
        for article_title, article_page in articles:
            lines.append(f"\n{'─'*60}")
            lines.append(f"📰 {article_title}")
            lines.append(f"📄 Page {article_page}")
            lines.append("─" * 60)
            lines.append("")
            
            # 找到下一篇文章的页码
            next_page = None
            for idx, (level, title, page) in enumerate(toc):
                if title.lower() == article_title.lower() or title.lower().startswith(article_title.lower()[:50]):
                    # 找到当前文章
                    if idx + 1 < len(toc):
                        next_page = toc[idx + 1][2]
                    break
            
            # 提取文章内容（最多3页）
            start_page = article_page - 1
            end_page = next_page - 1 if next_page else start_page + 3
            
            content_extracted = False
            for page_num in range(start_page, min(end_page, start_page + 3)):
                if page_num >= len(doc):
                    break
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    lines.append(text)
                    lines.append("")
                    content_extracted = True
            
            if not content_extracted:
                lines.append("[Content not available]")
            
            lines.append("")
    
    doc.close()
    return "\n".join(lines)

def save_full_content(content, pdf_path):
    """保存完整内容到文件"""
    date_str = "unknown"
    parts = pdf_path.split('/')
    for part in parts:
        if part.startswith('te_'):
            date_str = part[3:]
            break
    
    output_path = f"/home/codespace/.openclaw/workspace/economist_full_content_{date_str}.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 完整内容索引已保存到: {output_path}")
    return output_path

def send_to_telegram(message):
    """发送消息到 Telegram"""
    try:
        import subprocess
        import shlex
        
        # 分块发送
        chunks = []
        current_lines = []
        current_len = 0
        
        for line in message.split('\n'):
            line_len = len(line) + 1
            if current_len + line_len > 3500:
                chunks.append('\n'.join(current_lines))
                current_lines = [line]
                current_len = line_len
            else:
                current_lines.append(line)
                current_len += line_len
        
        if current_lines:
            chunks.append('\n'.join(current_lines))
        
        print(f"📦 消息将分成 {len(chunks)} 段发送")
        
        for idx, chunk in enumerate(chunks):
            print(f"  发送第 {idx+1}/{len(chunks)} 段...")
            
            quoted_message = shlex.quote(chunk)
            cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted_message}'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"  ⚠️ 发送失败: {result.stderr[:200]}")
            else:
                print(f"  ✓ 第 {idx+1} 段已发送")
                
    except Exception as e:
        print(f"  ⚠️ Telegram 发送出错: {e}")
        print("  💡 请查看保存的文件获取目录内容")

def main():
    print("🔄 更新仓库...")
    os.chdir(REPO_DIR)
    result = run("git pull")
    if result.returncode != 0:
        print(f"  ⚠️ git pull 警告: {result.stderr.strip()}")
    
    print("📄 查找最新 PDF...")
    pdf_path = get_latest_economist()
    if not pdf_path:
        print("❌ 未找到 PDF 文件")
        return 1
    
    print(f"✅ 找到: {pdf_path}")
    
    print("📑 从 Table of Contents 提取目录...")
    sections_data = extract_toc_from_pdf(pdf_path)
    
    total = sum(len(articles) for _, _, articles in sections_data)
    print(f"📊 共提取 {len(sections_data)} 个板块，{total} 篇文章")
    
    if total == 0:
        print("❌ 未提取到任何文章")
        return 1
    
    print("📝 格式化目录...")
    message = format_toc(sections_data, pdf_path)
    
    # 保存目录到文件
    save_to_file(message, pdf_path)
    
    # 提取完整文章内容
    print("📄 提取完整文章内容...")
    full_content = extract_all_articles_content(pdf_path, sections_data)
    save_full_content(full_content, pdf_path)
    
    # 打印预览
    print("\n" + "="*50)
    print(message[:2500])
    if len(message) > 2500:
        print(f"\n... (还有 {len(message)-2500} 字符)")
    print("="*50 + "\n")
    
    print("📤 发送目录到 Telegram...")
    send_to_telegram(message)
    
    print("✅ 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
