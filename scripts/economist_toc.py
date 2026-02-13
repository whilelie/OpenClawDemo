#!/usr/bin/env python3
"""
经济学人目录自动提取脚本
从 awesome-english-ebooks 仓库获取最新 PDF 并提取完整目录
结合 PDF 大纲和正文扫描
"""

import os
import sys
import subprocess
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

def find_section_pages(pdf_path):
    """
    扫描 PDF 正文页面，找出每个板块的起始页
    返回: [(section_name, start_page), ...]
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
    section_pages = []  # [(section_name, page), ...]
    found_sections = set()
    
    doc = fitz.open(pdf_path)
    
    # 扫描前 320 页寻找板块标题（确保覆盖 Science & technology, Culture 等）
    for page_num in range(min(320, len(doc))):
        page = doc[page_num]
        text = page.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            continue
        
        # 检查页面首行是否是板块标题
        first_line = lines[0] if lines else ""
        
        for sec_name in section_names:
            if sec_name not in found_sections:
                # 完全匹配或开始匹配
                if first_line == sec_name or first_line.startswith(sec_name + ' '):
                    section_pages.append((sec_name, page_num + 1))
                    found_sections.add(sec_name)
                    print(f"  找到板块: {sec_name} @ 第 {page_num + 1} 页")
                    break
    
    doc.close()
    return section_pages

def get_articles_from_toc(pdf_path):
    """
    从 PDF 大纲获取所有文章
    返回: [(title, page), ...]
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    doc.close()
    
    articles = []
    for level, title, page in toc:
        # 排除已知非文章条目
        if title in ['Politics', 'Business'] and page < 15:
            continue  # The world this week 的子板块
        if len(title) > 3:
            articles.append((title, page))
    
    return articles

def extract_toc(pdf_path):
    """
    结合板块页面信息和 TOC 文章信息，生成完整目录
    返回: [(section_name, section_cn, [(article_title, page), ...]), ...]
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
    
    section_cn_map = {s[0]: s[1] for s in sections_config}
    
    print("  扫描板块页面...")
    section_pages = find_section_pages(pdf_path)
    
    print(f"  找到 {len(section_pages)} 个板块")
    
    print("  获取文章列表...")
    articles = get_articles_from_toc(pdf_path)
    print(f"  TOC 中共有 {len(articles)} 篇文章")
    
    # 将文章分配到各个板块
    sections_data = []
    
    for i, (sec_name, sec_start_page) in enumerate(section_pages):
        # 确定当前板块的结束页
        if i + 1 < len(section_pages):
            sec_end_page = section_pages[i + 1][1]
        else:
            sec_end_page = 9999  # 最后一个板块到文档末尾
        
        # 找到属于该板块的文章
        sec_articles = []
        for title, page in articles:
            if sec_start_page <= page < sec_end_page:
                sec_articles.append((title, page))
        
        if sec_articles:
            sections_data.append((sec_name, section_cn_map.get(sec_name, sec_name), sec_articles))
            print(f"  ✓ {sec_name}: {len(sec_articles)} 篇文章")
    
    return sections_data

def format_toc(sections_data, pdf_path):
    """格式化目录为文本"""
    date_str = "Unknown"
    parts = pdf_path.split('/')
    for part in parts:
        if part.startswith('te_'):
            date_str = part[3:].replace('.', '/')
            break
    
    lines = [f"📰 The Economist | 经济学人 - {date_str}\n"]
    lines.append("=" * 50 + "\n")
    
    total_articles = 0
    for sec_en, sec_cn, articles in sections_data:
        total_articles += len(articles)
        lines.append(f"\n【{sec_en} | {sec_cn}】({len(articles)}篇)")
        lines.append("-" * 40)
        
        for title, page in articles:
            lines.append(f"• {title}")
            lines.append(f"  第 {page} 页")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append(f"\n总计: {len(sections_data)} 个板块, {total_articles} 篇文章")
    lines.append(f"\n文件: {pdf_path}")
    
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
            
            # 使用 shlex.quote 安全地转义消息内容
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
    
    print("📑 提取完整目录...")
    sections_data = extract_toc(pdf_path)
    
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
