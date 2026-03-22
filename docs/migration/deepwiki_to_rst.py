import os
import re
import sys
import json
from pathlib import Path

class DeepWikiToRST:
    def __init__(self, input_dir, output_dir, commit_id, config_file="migration/doc_config.json"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.commit_id = commit_id
        self.base_url = f"https://gitcode.com/openeuler/IB_Robot/blob/{self.commit_id}/"
        
        # 从 JSON 加载配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.id_to_label = config["id_to_label"]
            self.title_to_label = config["title_to_label"]
            self.hierarchy = config["hierarchy"]

    def md_table_to_rst(self, match):
        table_content = match.group(0).strip()
        rows = table_content.split('\n')
        if len(rows) < 3: return table_content
        try:
            headers = [c.strip() for c in rows[0].split('|') if c.strip()]
            num_cols = len(headers)
            data_rows = []
            for r in rows[2:]:
                if '|' in r:
                    cols = [c.strip() for c in r.split('|') if c.strip()]
                    if len(cols) < num_cols: cols.extend([''] * (num_cols - len(cols)))
                    else: cols = cols[:num_cols]
                    data_rows.append(cols)
            rst_table = "\n.. list-table::\n   :header-rows: 1\n\n"
            for h in headers:
                prefix = "   * - " if h == headers[0] else "     - "
                rst_table += f"{prefix}{h}\n"
            for row in data_rows:
                for i, cell in enumerate(row):
                    cell = cell.replace('<br/>', ' ').replace('<br>', ' ')
                    prefix = "   * - " if i == 0 else "     - "
                    rst_table += f"{prefix}{cell}\n"
            return rst_table + "\n"
        except:
            return table_content

    def get_url_from_text(self, text):
        # 移除可能的 URL 部分，只取路径和行号
        clean_text = text.split('(')[0].strip()
        parts = clean_text.split(':')
        path = parts[0]
        lines = ""
        if len(parts) > 1:
            line_range = parts[1]
            range_match = re.search(r'(\d+)(?:-(\d+))?', line_range)
            if range_match:
                start, end = range_match.group(1), range_match.group(2)
                lines = f"#L{start}-L{end}" if end else f"#L{start}"
        return f"{self.base_url}{path}{lines}"

    def fix_links(self, content):
        def replace_source(m):
            text = m.group(1).strip().replace('`', '')
            full_url = self.get_url_from_text(text)
            return f" `{text} <{full_url}>`__"

        content = re.sub(r'\[([^\]]+?)\]\(\)', replace_source, content)

        def replace_anchor_with_text(m):
            text, page_id = m.group(1), m.group(2)
            label = self.id_to_label.get(page_id)
            return f":ref:`{text} <ib_robot_{label}>`" if label else text
        content = re.sub(r'\[(.*?)\]\(#([\d\.]+)\)', replace_anchor_with_text, content)
        
        def replace_simple_anchor(m):
            inner = m.group(1)
            ids = re.findall(r'#([\d\.]+)', inner)
            results = []
            for pid in ids:
                label = self.id_to_label.get(pid)
                results.append(f":ref:`#{pid} <ib_robot_{label}>`" if label else f"#{pid}")
            return "(" + ", ".join(results) + ")"
        content = re.sub(r'\((#[\d\.,\s#]+)\)', replace_simple_anchor, content)
        
        content = re.sub(r'\[(.*?)\]\((http.*?)\)', r'`\1 <\2>`_', content)
        return content

    def convert_content(self, md_content, page_title=""):
        block_placeholders = []
        def protect_blocks(m):
            raw_content = m.group(1)
            placeholder = f"[[[BLOCK_{len(block_placeholders)}]]]"
            lines = raw_content.split('\n')
            first_line = lines[0].strip()
            if first_line == "mermaid":
                body = '\n'.join(lines[1:])
                indented = "\n".join("   " + line for line in body.strip('\n').split('\n'))
                rst_block = f"\n.. mermaid::\n\n{indented}\n\n"
            else:
                if first_line and ' ' not in first_line and re.match(r'^\w+$', first_line):
                    lang, body = first_line, '\n'.join(lines[1:])
                else:
                    lang, body = "text", raw_content
                indented = "\n".join("   " + line for line in body.strip('\n').split('\n'))
                rst_block = f"\n.. code-block:: {lang}\n\n{indented}\n\n"
            block_placeholders.append(rst_block)
            return placeholder

        content = re.sub(r'```(.*?)```', protect_blocks, md_content, flags=re.DOTALL)
        
        label = self.title_to_label.get(page_title, "")
        label_prefix = f".. _ib_robot_{label}:\n\n" if label else ""

        lines = content.split('\n')
        if lines and lines[0].strip().startswith("# "):
            content = '\n'.join(lines[1:])

        # 处理 <details> 块
        def convert_details(m):
            full_text = m.group(0)
            summary_match = re.search(r'<summary>(.*?)</summary>', full_text)
            summary = summary_match.group(1) if summary_match else "Relevant source files"
            body_match = re.search(r'</summary>(.*?)</details>', full_text, flags=re.DOTALL)
            body_md = body_match.group(1).strip() if body_match else ""
            
            # 转换 body
            lines = body_md.split('\n')
            html_body = ""
            in_list = False
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # 转换链接 [text](url) 或 [text]()
                def replace_md_link(lm):
                    text, url = lm.group(1), lm.group(2)
                    if not url or not url.startswith('http'):
                        url = self.get_url_from_text(text)
                    return f'<a href="{url}">{text}</a>'
                line = re.sub(r'\[(.*?)\]\((.*?)\)', replace_md_link, line)
                
                if line.startswith('- '):
                    if not in_list:
                        html_body += "   <ul>\n"
                        in_list = True
                    html_body += f"     <li>{line[2:]}</li>\n"
                else:
                    if in_list:
                        html_body += "   </ul>\n"
                        in_list = False
                    html_body += f"   <p>{line}</p>\n"
            if in_list: html_body += "   </ul>\n"
            
            return f"\n.. raw:: html\n\n   <details>\n   <summary>{summary}</summary>\n{html_body}   </details>\n"

        content = re.sub(r'<details>.*?</details>', convert_details, content, flags=re.DOTALL)

        def replace_h1(m):
            t = m.group(1).strip()
            return f"\n{label_prefix}{t}\n" + "#" * (len(t) * 2) + "\n"
        content = re.sub(r'^# (.*)$', replace_h1, content, flags=re.MULTILINE)

        def replace_h2(m):
            t = m.group(1).strip()
            return f"\n{t}\n" + "=" * (len(t) * 2) + "\n"
        content = re.sub(r'^## (.*)$', replace_h2, content, flags=re.MULTILINE)

        def replace_h3(m):
            t = m.group(1).strip()
            return f"\n{t}\n" + "-" * (len(t) * 2) + "\n"
        content = re.sub(r'^### (.*)$', replace_h3, content, flags=re.MULTILINE)

        def replace_h4(m):
            t = m.group(1).strip()
            return f"\n{t}\n" + "^" * (len(t) * 2) + "\n"
        content = re.sub(r'^#### (.*)$', replace_h4, content, flags=re.MULTILINE)

        content = re.sub(r'([^\n])\n(\s*)([-*] |\d+\. )', r'\1\n\n\2\3', content)
        content = re.sub(r'^\s*---\s*$', r'\n----\n', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*`([^`]+)`\*\*', r'``\1``', content)
        content = re.sub(r'(?<!`)`([^`\n]+)`(?!`)', r'``\1``', content)
        content = re.sub(r'((?:\|.*\|(?:\n|$))+)', self.md_table_to_rst, content)
        content = self.fix_links(content)

        for i, rst_block in enumerate(block_placeholders):
            content = content.replace(f"[[[BLOCK_{i}]]]", rst_block)

        content = content.strip()
        while content.endswith('----'):
            content = re.sub(r'\n----\s*$', '', content).strip()
        return content

    def run(self):
        if not self.output_dir.exists(): self.output_dir.mkdir(parents=True)

        md_files = list(self.input_dir.glob("*.md"))
        title_to_content = {}
        for f in md_files:
            with open(f, 'r', encoding='utf-8') as f_in:
                text = f_in.read()
                title = text.split('\n')[0].replace('# ', '').strip()
                title_to_content[title] = text

        index_toctree = []

        for name, config in self.hierarchy.items():
            if name.endswith(".rst"):
                print(f"Generating {name}...")
                title = config["title"]
                if title in title_to_content:
                    converted = self.convert_content(title_to_content[title], title)
                    with open(self.output_dir / name, 'w', encoding='utf-8') as f_out: f_out.write(converted)
                    index_toctree.append(name)
            else:
                print(f"Creating directory {name}...")
                dir_path = self.output_dir / name
                if not dir_path.exists(): dir_path.mkdir(parents=True)
                
                sub_toctree = []
                main_title = config["title"]
                
                if main_title in title_to_content:
                    print(f"  Generating introduction for {name}...")
                    intro_content = self.convert_content(title_to_content[main_title], main_title)
                    with open(dir_path / "introduction.rst", 'w', encoding='utf-8') as f_out:
                        f_out.write(intro_content)
                    sub_toctree.append("introduction.rst")
                
                for sub_file, sub_title in config["subs"].items():
                    print(f"  Generating sub-page {name}/{sub_file}...")
                    if sub_title in title_to_content:
                        sub_content = self.convert_content(title_to_content[sub_title], sub_title)
                        with open(dir_path / sub_file, 'w', encoding='utf-8') as f_out: f_out.write(sub_content)
                        sub_toctree.append(sub_file)
                
                index_content = f"{main_title}\n" + "#" * (len(main_title) * 2) + "\n\n"
                index_content += f"本章节包含关于 {main_title} 的详细指南和参考资料。\n\n"
                index_content += ".. toctree::\n   :maxdepth: 1\n\n"
                for item in sub_toctree: index_content += f"   {item}\n"
                
                with open(dir_path / "index.rst", 'w', encoding='utf-8') as f_out: f_out.write(index_content)
                index_toctree.append(f"{name}/index.rst")

        print("Generating main index.rst...")
        main_index = ".. _ib_robot_intro:\n\nIB-Robot 具身智能套件\n################################\n\nIB-Robot（Intelligence Boom Robot）是一个将 Hugging Face LeRobot 机器学习生态系统与 ROS 2 机器人中间件连接起来的集成开发框架，旨在实现端到端的具身智能（Embodied AI）工作流。\n\n.. toctree::\n   :maxdepth: 2\n   :caption: 内容\n\n"
        for item in index_toctree: main_index += f"   {item}\n"
        with open(self.output_dir / "index.rst", 'w', encoding='utf-8') as f_out: f_out.write(main_index)

if __name__ == "__main__":
    commit_id = "9e382ea2320c3260b03e9c838696f8ac89eb8944"
    if len(sys.argv) > 1: commit_id = sys.argv[1]
    converter = DeepWikiToRST("migration/raw_md", "docs/source/features/ib_robot", commit_id)
    converter.run()
