#!/usr/bin/env python3
"""
经济学人文章提取脚本
根据标题从 PDF 提取完整文章内容，并使用 Kimi 翻译
"""

import os
import sys
import urllib.request
import json
import fitz  # PyMuPDF

REPO_DIR = "/workspaces/awesome-english-ebooks"
KIMI_API_KEY = "sk-xdLnWGrw3hrjJnNk9QpAN4jYd4gSYRc6675p0aVqa7cO1cY3"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

def translate_with_kimi(text):
    """使用 Kimi API 翻译文本"""
    if not text.strip():
        return ""
    
    # 跳过太短的文本
    if len(text.strip()) < 10:
        return "[短文本，略]"
    
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
                    "content": "你是一个专业的英译中翻译助手。请将以下英文翻译成自然流畅的中文。只返回翻译结果，不要解释。"
                },
                {
                    "role": "user",
                    "content": f"请翻译：{text}"
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
            return translation
            
    except Exception as e:
        return f"[翻译失败: {str(e)[:50]}]"

def translate_paragraphs(paragraphs):
    """批量翻译段落"""
    translated = []
    total = len(paragraphs)
    
    for i, para in enumerate(paragraphs):
        if para.strip():
            print(f"  翻译段落 {i+1}/{total}...", end=" ", flush=True)
            cn = translate_with_kimi(para)
            print("✓")
            translated.append((para, cn))
        else:
            translated.append(("", ""))
    
    return translated

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

def normalize_text(text):
    """标准化文本，处理不同的引号字符"""
    text = text.replace('\u2019', "'").replace('\u2018', "'")  # 弯单引号
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # 弯双引号
    text = text.replace('\u2013', '-').replace('\u2014', '-')  # en-dash 和 em-dash
    return text.lower().strip()

def find_article_in_pdf(pdf_path, article_title):
    """
    在 PDF 中查找文章并提取内容
    返回: (article_start_page, article_text, paragraphs)
    """
    doc = fitz.open(pdf_path)
    
    # 1. 从 TOC 找到文章起始页
    toc = doc.get_toc()
    start_page = None
    end_page = None
    
    article_title_normalized = normalize_text(article_title)
    
    for i, (level, title, page) in enumerate(toc):
        toc_title_normalized = normalize_text(title)
        if toc_title_normalized == article_title_normalized or toc_title_normalized.startswith(article_title_normalized[:50]):
            start_page = page - 1  # 转换为 0-based
            if i + 1 < len(toc):
                end_page = toc[i + 1][2] - 1
            else:
                end_page = len(doc)
            break
    
    if start_page is None:
        doc.close()
        return None, f"未找到文章: {article_title}", []
    
    # 2. 提取文章内容
    paragraphs = []
    
    for page_num in range(start_page, min(end_page, start_page + 5)):
        if page_num >= len(doc):
            break
        page = doc[page_num]
        text = page.get_text()
        # 将文本分割成段落
        page_paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraphs.extend(page_paras)
    
    doc.close()
    return start_page + 1, "", paragraphs

def main():
    if len(sys.argv) < 2:
        print("用法: python3 economist_article.py \"文章标题\"")
        print('示例: python3 economist_article.py \"Don\'t ban teenagers from social media\"')
        return 1
    
    article_title = sys.argv[1]
    
    print("📄 查找最新 PDF...")
    pdf_path = get_latest_economist()
    if not pdf_path:
        print("❌ 未找到 PDF 文件")
        return 1
    
    print(f"🔍 搜索文章: {article_title}")
    page_num, _, paragraphs = find_article_in_pdf(pdf_path, article_title)
    
    if page_num is None:
        print("未找到文章")
        return 1
    
    print(f"✅ 找到文章在第 {page_num} 页")
    print(f"🌐 开始翻译 {len(paragraphs)} 个段落...")
    print()
    
    # 翻译段落
    translated_paragraphs = translate_paragraphs(paragraphs)
    
    # 构建输出
    output = []
    output.append("=" * 60)
    output.append(f"📰 {article_title}")
    output.append(f"📄 第 {page_num} 页")
    output.append("=" * 60)
    output.append("")
    
    for en, cn in translated_paragraphs:
        if en:
            output.append(en)
            output.append(f"【译】{cn}")
            output.append("")
    
    output.append("=" * 60)
    output.append("翻译由 Kimi AI 提供")
    output.append("=" * 60)
    
    result = "\n".join(output)
    print(result)
    
    # 保存到文件
    date_str = pdf_path.split('/')[-2][3:]
    safe_title = "".join(c if c.isalnum() else "_" for c in article_title[:30])
    output_path = f"/home/codespace/.openclaw/workspace/article_{date_str}_{safe_title}.txt"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print()
    print(f"💾 翻译后的文章已保存到: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
