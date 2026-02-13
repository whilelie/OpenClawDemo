#!/usr/bin/env python3
"""
经济学人目录自动提取脚本
从 PDF 末尾的 Table of Contents 页面提取完整目录
"""

import os
import sys
import subprocess
import urllib.parse
import fitz  # PyMuPDF
from datetime import datetime

REPO_DIR = "/workspaces/awesome-english-ebooks"
TELEGRAM_CHAT_ID = "1268358344"

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

def format_toc(sections_data, pdf_path):
    """格式化目录为 Markdown 格式，带可点击链接"""
    date_str = "Unknown"
    parts = pdf_path.split('/')
    for part in parts:
        if part.startswith('te_'):
            date_str = part[3:].replace('.', '/')
            break
    
    lines = [f"📰 *The Economist | 经济学人* - {date_str}\n"]
    lines.append("─" * 40 + "\n")
    
    total_articles = 0
    for sec_en, sec_cn, articles in sections_data:
        total_articles += len(articles)
        # 板块标题加粗
        lines.append(f"\n*{sec_en}* ｜ {sec_cn}")
        
        for title, page in articles:
            # 构建搜索链接（使用标题搜索）
            # 对标题进行 URL 编码
            import urllib.parse
            search_query = urllib.parse.quote(f"{title} site:economist.com")
            search_url = f"https://www.google.com/search?q={search_query}"
            
            # Markdown 格式：标题可点击，页码在右侧
            lines.append(f"• [{title}]({search_url}) ｜ _p.{page}_")
        
        lines.append("")
    
    lines.append("─" * 40)
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
    
    print("📝 格式化...")
    message = format_toc(sections_data, pdf_path)
    
    # 保存到文件
    save_to_file(message, pdf_path)
    
    # 打印预览
    print("\n" + "="*50)
    print(message[:2500])
    if len(message) > 2500:
        print(f"\n... (还有 {len(message)-2500} 字符)")
    print("="*50 + "\n")
    
    print("📤 发送到 Telegram...")
    send_to_telegram(message)
    
    print("✅ 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
