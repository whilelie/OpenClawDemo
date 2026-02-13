#!/usr/bin/env python3
"""
经济学人交互式目录 - 简化版
发送带编号的文章列表，支持回复编号查看
"""

import os
import sys
import subprocess
import urllib.parse
import urllib.request
import json
import fitz

REPO_DIR = "/workspaces/awesome-english-ebooks"
TELEGRAM_CHAT_ID = "1268358344"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# 全局文章列表
articles_list = []  # [(number, title, section, page), ...]

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def get_latest_economist():
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

def normalize_text(text):
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text.lower().strip()

def extract_toc_simple(pdf_path):
    """简化版目录提取"""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
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
    section_cn = {s[0]: s[1] for s in sections_config}
    
    # 获取文章列表
    articles = []
    current_section = None
    
    for level, title, page in toc:
        if title in section_names:
            current_section = title
            continue
        
        if current_section and len(title) > 3:
            # 排除子板块标记
            if title in ['Politics', 'Business'] and page < 15:
                pass  # 是文章
            elif len(title) > 3:
                articles.append((title, current_section, section_cn.get(current_section, current_section), page))
    
    doc.close()
    return articles

def send_telegram_message(message):
    """发送 Telegram 消息"""
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
    
    print(f"📦 将分成 {len(chunks)} 段发送")
    
    for idx, chunk in enumerate(chunks):
        print(f"  发送第 {idx+1}/{len(chunks)} 段...", end=" ", flush=True)
        quoted = shlex.quote(chunk)
        cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
        result = run(cmd)
        if result.returncode != 0:
            print(f"✗ ({result.stderr[:100]})")
        else:
            print("✓")

def create_numbered_menu(articles, date_str):
    """创建带编号的文章菜单"""
    global articles_list
    articles_list = []
    
    lines = []
    lines.append(f"📰 *经济学人 {date_str}*")
    lines.append("═" * 40)
    lines.append("")
    lines.append("📖 *文章目录* (回复 `/read 编号` 查看)")
    lines.append("═" * 40)
    
    current_section = None
    article_num = 0
    
    for title, section_en, section_cn, page in articles:
        if section_en != current_section:
            current_section = section_en
            lines.append(f"\n📂 *{section_en}* ｜ {section_cn}")
        
        article_num += 1
        
        # 截断长标题
        display_title = title[:40] + "..." if len(title) > 40 else title
        
        lines.append(f"`{article_num:2d}`. {display_title} ｜ p.{page}")
        articles_list.append((article_num, title, section_cn, page))
    
    lines.append("")
    lines.append("═" * 40)
    lines.append(f"_共 {article_num} 篇文章_")
    lines.append("")
    lines.append("💡 *使用示例*：")
    lines.append("回复 `/read 1` 查看第1篇文章")
    lines.append("回复 `/read 5` 查看第5篇文章")
    
    return "\n".join(lines)

def main():
    print("📄 查找最新 PDF...")
    pdf_path = get_latest_economist()
    if not pdf_path:
        print("❌ 未找到 PDF 文件")
        return 1
    
    date_str = pdf_path.split('/')[-2][3:].replace('.', '/')
    print(f"✅ 找到: {date_str} 期刊")
    
    # 提取目录
    print("📑 提取文章列表...")
    articles = extract_toc_simple(pdf_path)
    print(f"✅ 找到 {len(articles)} 篇文章")
    
    # 创建菜单
    print("📋 创建编号菜单...")
    menu_text = create_numbered_menu(articles, date_str)
    
    # 保存索引
    index_path = f"/home/codespace/.openclaw/workspace/economist_index_{date_str.replace('/', '.')}.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump([{
            'number': num,
            'title': title,
            'section': section,
            'page': page
        } for num, title, section, page in articles_list], f, ensure_ascii=False, indent=2)
    print(f"💾 索引已保存: {index_path}")
    
    # 发送菜单
    print("📤 发送目录到 Telegram...")
    send_telegram_message(menu_text)
    
    # 发送提示消息
    hint = """💡 *阅读指南*

1️⃣ 查看文章列表中的编号
2️⃣ 回复 `/read 编号` 查看文章
3️⃣ 例如：回复 `/read 1` 查看第1篇

文章将以 *中英对照* 格式发送，包含：
• 英文原文
• 中文翻译（由 Kimi AI 提供）

📝 提示：编号范围是 1-78"""
    
    print("📤 发送使用说明...")
    send_telegram_message(hint)
    
    print("✅ 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
