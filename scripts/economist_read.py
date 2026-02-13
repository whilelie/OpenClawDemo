#!/usr/bin/env python3
"""
根据编号查看经济学人文章（中英对照）
用法: python3 economist_read.py 编号
"""

import os
import sys
import json
import urllib.request
import fitz

REPO_DIR = "/workspaces/awesome-english-ebooks"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

def load_article_index():
    """加载文章索引"""
    # 找到最新的索引文件
    workspace = "/home/codespace/.openclaw/workspace"
    index_files = [f for f in os.listdir(workspace) if f.startswith('economist_index_') and f.endswith('.json')]
    if not index_files:
        return None
    
    index_files.sort(reverse=True)
    index_path = os.path.join(workspace, index_files[0])
    
    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_latest_pdf():
    """获取最新 PDF"""
    economist_dir = os.path.join(REPO_DIR, "01_economist")
    dirs = [d for d in os.listdir(economist_dir) if d.startswith("te_")]
    dirs.sort(reverse=True)
    pdf_path = os.path.join(economist_dir, dirs[0], f"TheEconomist.{dirs[0][3:]}.pdf")
    return pdf_path

def normalize_text(text):
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text.lower().strip()

def translate_text(text):
    """使用 Kimi 翻译"""
    if not text.strip() or len(text.strip()) < 20:
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
                    "content": "将以下英文翻译成自然流畅的中文。只返回翻译结果，不要解释。"
                },
                {
                    "role": "user",
                    "content": text[:600]  # 限制长度
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
    except Exception as e:
        return f"[翻译错误: {str(e)[:50]}]"

def extract_article(pdf_path, title):
    """提取文章内容"""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    
    title_norm = normalize_text(title)
    start_page = None
    end_page = None
    
    for i, (level, toc_title, page) in enumerate(toc):
        toc_norm = normalize_text(toc_title)
        if toc_norm == title_norm or toc_norm.startswith(title_norm[:50]):
            start_page = page - 1
            if i + 1 < len(toc):
                end_page = toc[i + 1][2] - 1
            else:
                end_page = len(doc)
            break
    
    if start_page is None:
        doc.close()
        return []
    
    paragraphs = []
    for page_num in range(start_page, min(end_page, start_page + 3)):
        if page_num >= len(doc):
            break
        page = doc[page_num]
        text = page.get_text()
        paras = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 30]
        paragraphs.extend(paras)
    
    doc.close()
    return paragraphs

def send_to_telegram(message):
    """发送到 Telegram"""
    import subprocess
    import shlex
    
    TELEGRAM_CHAT_ID = "1268358344"
    
    # 分块
    chunks = []
    current = []
    current_len = 0
    
    for line in message.split('\n'):
        if current_len + len(line) > 3500:
            chunks.append('\n'.join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    
    if current:
        chunks.append('\n'.join(current))
    
    for idx, chunk in enumerate(chunks):
        quoted = shlex.quote(chunk)
        cmd = f'openclaw message send --channel telegram --target {TELEGRAM_CHAT_ID} --message {quoted}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ 第 {idx+1}/{len(chunks)} 段已发送")
        else:
            print(f"  ✗ 发送失败: {result.stderr[:100]}")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 economist_read.py <编号>")
        print("示例: python3 economist_read.py 1")
        print("      python3 economist_read.py 5")
        return 1
    
    try:
        article_num = int(sys.argv[1])
    except ValueError:
        print("❌ 编号必须是数字")
        return 1
    
    # 加载索引
    index = load_article_index()
    if not index:
        print("❌ 未找到文章索引，请先运行 economist_interactive.py")
        return 1
    
    # 查找文章
    article = None
    for item in index:
        if item['number'] == article_num:
            article = item
            break
    
    if not article:
        print(f"❌ 未找到编号 {article_num} 的文章")
        print(f"可用范围: 1-{len(index)}")
        return 1
    
    title = article['title']
    section = article['section']
    page = article['page']
    
    print(f"📰 [{article_num}] {title}")
    print(f"📄 {section} ｜ 第 {page} 页")
    print("─" * 50)
    
    # 提取内容
    pdf_path = get_latest_pdf()
    paragraphs = extract_article(pdf_path, title)
    
    if not paragraphs:
        print("❌ 无法提取文章内容")
        return 1
    
    print(f"🌐 翻译 {min(3, len(paragraphs))} 段内容...")
    
    # 翻译
    translated = []
    for i, para in enumerate(paragraphs[:3]):
        print(f"  翻译段落 {i+1}...", end=" ", flush=True)
        cn = translate_text(para)
        print("✓")
        translated.append((para[:500], cn))
    
    # 构建消息
    lines = []
    lines.append("=" * 50)
    lines.append(f"📰 *{title}*")
    lines.append(f"📂 {section} ｜ 第 {page} 页")
    lines.append("=" * 50)
    lines.append("")
    
    for en, cn in translated:
        lines.append(en)
        lines.append("")
        lines.append(f"【译】{cn}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("💡 回复 `/read 编号` 查看其他文章")
    
    message = "\n".join(lines)
    
    # 保存到文件
    date_str = pdf_path.split('/')[-2][3:]
    safe_title = "".join(c if c.isalnum() else "_" for c in title[:25])
    output_path = f"/home/codespace/.openclaw/workspace/article_{date_str}_{safe_title}.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(message)
    print(f"💾 已保存: {output_path}")
    
    # 发送到 Telegram
    print("📤 发送到 Telegram...")
    send_to_telegram(message)
    
    print("✅ 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
