#!/usr/bin/env python3
"""
经济学人交互式目录脚本
发送带编号的文章菜单，支持回复编号查看文章
"""

import os
import sys
import subprocess
import urllib.parse
import urllib.request
import json
import fitz
from datetime import datetime

REPO_DIR = "/workspaces/awesome-english-ebooks"
TELEGRAM_CHAT_ID = "1268358344"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# 全局文章索引
article_index = {}  # {number: (title, section, page)}

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

def translate_title(title):
    """翻译标题"""
    simple_map = {
        "Politics": "政治",
        "Business": "商业", 
        "The weekly cartoon": "本周漫画",
    }
    if title in simple_map:
        return simple_map[title]
    
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
                    "content": "将经济学人文章标题翻译成简洁的中文，只返回翻译结果。"
                },
                {
                    "role": "user",
                    "content": f"翻译：{title}"
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
            return result['choices'][0]['message']['content'].strip().strip('"')
    except:
        return "[待译]"

def normalize_text(text):
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text.lower().strip()

def extract_article_content(pdf_path, article_title):
    """提取文章内容"""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
    start_page = None
    end_page = None
    article_title_norm = normalize_text(article_title)
    
    for i, (level, title, page) in enumerate(toc):
        title_norm = normalize_text(title)
        if title_norm == article_title_norm or title_norm.startswith(article_title_norm[:50]):
            start_page = page - 1
            if i + 1 < len(toc):
                end_page = toc[i + 1][2] - 1
            else:
                end_page = len(doc)
            break
    
    if start_page is None:
        doc.close()
        return None
    
    paragraphs = []
    for page_num in range(start_page, min(end_page, start_page + 5)):
        if page_num >= len(doc):
            break
        page = doc[page_num]
        text = page.get_text()
        paras = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 20]
        paragraphs.extend(paras)
    
    doc.close()
    return paragraphs

def translate_paragraph(text):
    """翻译段落"""
    if not text.strip() or len(text.strip()) < 30:
        return None
    
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
                    "content": "将英文翻译成自然流畅的中文，只返回翻译结果。"
                },
                {
                    "role": "user",
                    "content": f"翻译：{text[:500]}"  # 限制长度
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
            return result['choices'][0]['message']['content'].strip()
    except:
        return "[翻译失败]"

def send_telegram_message(message, buttons=None):
    """发送 Telegram 消息，可选带按钮"""
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
    
    for idx, chunk in enumerate(chunks):
        quoted = shlex.quote(chunk)
        cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
        
        if buttons and idx == len(chunks) - 1:  # 只在最后一块添加按钮
            buttons_json = shlex.quote(json.dumps(buttons))
            cmd += f' --buttons {buttons_json}'
        
        result = run(cmd)
        if result.returncode != 0:
            print(f"  ⚠️ 发送失败: {result.stderr[:200]}")
        else:
            print(f"  ✓ 第 {idx+1}/{len(chunks)} 段已发送")

def create_interactive_menu(sections_data, date_str):
    """创建交互式菜单"""
    global article_index
    article_index = {}
    
    lines = [f"📰 *经济学人 {date_str}*"]
    lines.append("─" * 40)
    lines.append("")
    lines.append("💡 *阅读指南*")
    lines.append("• 回复 `/read 编号` 查看文章（中英对照）")
    lines.append("• 例如：`/read 1` 查看第一篇文章")
    lines.append("")
    lines.append("=" * 40)
    
    article_num = 0
    buttons_rows = []
    
    for sec_en, sec_cn, articles in sections_data:
        lines.append(f"\n📂 *{sec_en}* ｜ {sec_cn}")
        lines.append("")
        
        # 每行最多3个按钮
        current_row = []
        for title, page in articles:
            article_num += 1
            cn_title = translate_title(title)
            
            # 截断长标题
            display_title = cn_title[:15] + "..." if len(cn_title) > 15 else cn_title
            
            lines.append(f"`{article_num:2d}`. {display_title} ｜ p.{page}")
            
            # 保存到索引
            article_index[article_num] = (title, sec_cn, page)
            
            # 创建按钮
            btn_text = f"{article_num}"
            # 使用特殊的 callback_data 格式
            callback_data = f"article:{article_num}:{title[:20]}"
            current_row.append({
                "text": btn_text,
                "callback_data": callback_data
            })
            
            if len(current_row) == 5:  # 每行5个按钮
                buttons_rows.append(current_row)
                current_row = []
        
        if current_row:
            buttons_rows.append(current_row)
            current_row = []
    
    lines.append("")
    lines.append("=" * 40)
    lines.append(f"_共 {article_num} 篇文章_")
    lines.append("")
    lines.append("📝 *快速回复格式*：")
    lines.append("`/read 1` - 查看第1篇文章")
    lines.append("`/read 5` - 查看第5篇文章")
    
    return "\n".join(lines), buttons_rows

def send_article_by_number(pdf_path, article_num):
    """发送指定编号的文章"""
    if article_num not in article_index:
        print(f"❌ 无效的文章编号: {article_num}")
        print(f"可用编号: 1-{max(article_index.keys())}")
        return False
    
    title, section, page = article_index[article_num]
    print(f"📄 提取文章 [{article_num}]: {title}")
    print(f"   板块: {section}, 页码: {page}")
    
    # 提取内容
    paragraphs = extract_article_content(pdf_path, title)
    if not paragraphs:
        print("❌ 无法提取文章内容")
        return False
    
    # 翻译前3段
    print(f"🌐 翻译 {min(3, len(paragraphs))} 段内容...")
    translated = []
    for i, para in enumerate(paragraphs[:3]):
        print(f"  翻译段落 {i+1}...", end=" ", flush=True)
        cn = translate_paragraph(para)
        print("✓")
        translated.append((para[:400], cn))  # 限制长度
    
    # 构建输出
    lines = []
    lines.append("=" * 50)
    lines.append(f"📰 *{title}*")
    lines.append(f"📂 {section} ｜ 第 {page} 页")
    lines.append("=" * 50)
    lines.append("")
    
    for en, cn in translated:
        lines.append(en)
        lines.append(f"【译】{cn}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("💡 回复 `/menu` 返回目录")
    
    message = "\n".join(lines)
    send_telegram_message(message)
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description='经济学人交互式目录')
    parser.add_argument('--read', type=int, help='阅读指定编号的文章')
    args = parser.parse_args()
    
    print("📄 查找最新 PDF...")
    pdf_path = get_latest_economist()
    if not pdf_path:
        print("❌ 未找到 PDF 文件")
        return 1
    
    date_str = pdf_path.split('/')[-2][3:].replace('.', '/')
    print(f"✅ 找到: {date_str} 期刊")
    
    # 提取目录
    print("📑 提取目录...")
    from economist_toc import extract_toc_from_pdf
    sections_data = extract_toc_from_pdf(pdf_path)
    
    if args.read:
        # 发送指定文章
        print(f"📖 发送文章 #{args.read}...")
        send_article_by_number(pdf_path, args.read)
    else:
        # 发送交互式菜单
        print("📋 创建交互式菜单...")
        menu_text, buttons = create_interactive_menu(sections_data, date_str)
        
        # 保存索引到文件
        index_path = f"/home/codespace/.openclaw/workspace/article_index_{date_str.replace('/', '.')}.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in article_index.items()}, f, ensure_ascii=False, indent=2)
        print(f"💾 文章索引已保存: {index_path}")
        
        # 发送菜单
        print("📤 发送菜单到 Telegram...")
        send_telegram_message(menu_text, buttons if buttons else None)
        print("✅ 完成!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
