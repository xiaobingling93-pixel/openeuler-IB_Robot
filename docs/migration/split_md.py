import os
import re

def split_raw_md(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改分割正则，适应 # Page: Title 格式
    pages = re.split(r'# Page: ', content)
    
    for page in pages[1:]:
        lines = page.strip().split('\n')
        full_title = lines[0].strip()
        
        # 将标题转换为文件名：移除特殊字符，空格换下划线，转小写
        filename = re.sub(r'[^\w\s]', '', full_title).strip().replace(' ', '_').lower() + ".md"
        
        out_path = os.path.join(output_dir, filename)
        print(f"Saving: {full_title} -> {out_path}")
        
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(f"# {full_title}\n\n" + '\n'.join(lines[1:]))

if __name__ == "__main__":
    split_raw_md("migration/IB_Robot_doc_raw.md", "migration/raw_md")
