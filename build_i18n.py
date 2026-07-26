#!/usr/bin/env python3
import json
import os
import re
import shutil

BASE_DIR = r"C:\Users\HP\Desktop\Prior Kredit\.proyektlərim\kaliforniya"
LANGS = ["es", "zh", "ja", "de"]
HTML_FILES = [
    "index.html",
    "about.html",
    "contact.html",
    "privacy.html",
    "terms.html",
    "404.html",
    "blog.html"
]

with open(os.path.join(BASE_DIR, "i18n_dict.json"), "r", encoding="utf-8") as f:
    i18n_dict = json.load(f)

def get_lang_switcher():
    return """
    <!-- Language Switcher -->
    <div class="fixed top-4 right-4 z-50">
        <select id="lang-switcher" onchange="changeLanguage(this.value)" class="glass-input p-1.5 rounded-lg text-xs font-bold text-gray-700 outline-none cursor-pointer bg-white/90 shadow-sm border border-gray-200 hover:border-red-400 transition-colors">
            <option value="en">🇺🇸 EN</option>
            <option value="es">🇪🇸 ES</option>
            <option value="zh">🇨🇳 ZH</option>
            <option value="ja">🇯🇵 JA</option>
            <option value="de">🇩🇪 DE</option>
        </select>
    </div>
    <script>
        function changeLanguage(lang) {
            localStorage.setItem('preferred_lang', lang);
            const path = window.location.pathname;
            const search = window.location.search;
            let newPath = path;
            
            // Remove current language prefix if exists
            newPath = newPath.replace(/^\\/(es|zh|ja|de)\\//, '/');
            if (newPath === '/es' || newPath === '/zh' || newPath === '/ja' || newPath === '/de') newPath = '/';
            
            if (lang !== 'en') {
                if (newPath === '/') newPath = '/' + lang + '/';
                else newPath = '/' + lang + newPath;
            }
            window.location.href = newPath + search;
        }
        
        document.addEventListener("DOMContentLoaded", () => {
            const path = window.location.pathname;
            let currentLang = 'en';
            const match = path.match(/^\\/(es|zh|ja|de)(\\/|$)/);
            if (match) currentLang = match[1];
            const select = document.getElementById('lang-switcher');
            if (select) select.value = currentLang;
        });
    </script>
    """

def get_auto_redirect():
    return """
    <script>
        (function() {
            const path = window.location.pathname;
            const isLangDir = /^\\/(es|zh|ja|de)(\\/|$)/.test(path);
            if (!isLangDir) {
                const preferred = localStorage.getItem('preferred_lang');
                if (preferred && preferred !== 'en') {
                    const search = window.location.search;
                    let newPath = path;
                    if (newPath === '/') newPath = '/' + preferred + '/';
                    else newPath = '/' + preferred + newPath;
                    window.location.replace(newPath + search);
                }
            }
        })();
    </script>
    """

def rewrite_paths(html, lang_code):
    # Absolute paths for static assets so they work from subdirectories
    html = re.sub(r'href="(favicon/[^"]+)"', r'href="/\1"', html)
    html = re.sub(r'src="(favicon/[^"]+)"', r'src="/\1"', html)
    html = re.sub(r'href="site\.webmanifest"', r'href="/site.webmanifest"', html)
    html = re.sub(r'src="(gtfs/data\.js)"', r'src="/\1"', html)
    
    # Prefix internal links
    prefix = "/" if lang_code == "en" else f"/{lang_code}/"
    for page in ["index.html", "about.html", "contact.html", "privacy.html", "terms.html", "blog.html"]:
        html = re.sub(r'href="' + page + r'"', f'href="{prefix}{page}"', html)
    
    # Update hreflang tags for SEO
    hreflangs = []
    for l in ["en"] + LANGS:
        p = "/" if l == "en" else f"/{l}/"
        hreflangs.append(f'<link rel="alternate" hreflang="{l}" href="https://sf-sanjosetrain.com{p}" />')
    hreflang_str = "\n    ".join(hreflangs)
    html = html.replace('<head>', f'<head>\n    {hreflang_str}')
    
    # Set html lang
    html = re.sub(r'<html lang="en"', f'<html lang="{lang_code}"', html)
    
    return html

def process_content(html, filepath, lang_code):
    # 1. Rewrite paths
    html = rewrite_paths(html, lang_code)
    
    # 2. Inject Language Switcher
    if "<body" in html:
        html = re.sub(r'(<body[^>]*>)', r'\1\n' + get_lang_switcher(), html)
        
    # 3. Inject auto-redirect (only on English files)
    if lang_code == "en" and "<head>" in html:
        html = html.replace('<head>', '<head>\n' + get_auto_redirect())

    # Prevent Google Translate and similar from auto-translating the site
    if "<head>" in html:
        html = html.replace('<head>', '<head>\n    <meta name="google" content="notranslate">\n    <meta name="robots" content="notranslate">')
    
    # Add translate="no" to the html tag
    html = re.sub(r'(<html[^>]*)', r'\1 translate="no"', html, count=1)

    # 4. Translate strings
    if lang_code != "en":
        # Sort keys by length descending to prevent partial replacements
        sorted_texts = sorted(i18n_dict["texts"].items(), key=lambda x: len(x[0]), reverse=True)
        for en_text, translations in sorted_texts:
            if lang_code in translations:
                target_text = translations[lang_code]
                # Simple replace. Be careful with HTML overlap, but exact strings should be safe.
                html = html.replace(en_text, target_text)

        # 5. Translate JS Station variables (if index.html)
        if filepath == "index.html":
            # the JS uses the stations array. The JSON has "stations".
            for st_id, translations in i18n_dict["stations"].items():
                if lang_code in translations:
                    target_name = translations[lang_code]
                    # The JS defines stations in a list of objects: {id: 'san_francisco', name: 'San Francisco'}
                    # We can use regex to replace the name property for that specific ID
                    html = re.sub(rf"\{{id: '{st_id}', name: '[^']+'\}}", f"{{id: '{st_id}', name: '{target_name}'}}", html)

    return html

def main():
    original_contents = {}
    for f in HTML_FILES:
        with open(os.path.join(BASE_DIR, f), "r", encoding="utf-8") as file:
            original_contents[f] = file.read()
            
    print("Building English base with language switcher...")
    for f in HTML_FILES:
        processed = process_content(original_contents[f], f, "en")
        with open(os.path.join(BASE_DIR, f), "w", encoding="utf-8") as out_f:
            out_f.write(processed)

    for lang in LANGS:
        print(f"Building {lang} translation...")
        lang_dir = os.path.join(BASE_DIR, lang)
        os.makedirs(lang_dir, exist_ok=True)
        
        for f in HTML_FILES:
            processed = process_content(original_contents[f], f, lang)
            out_path = os.path.join(lang_dir, f)
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(processed)

    print("All language versions built successfully.")

if __name__ == "__main__":
    main()
