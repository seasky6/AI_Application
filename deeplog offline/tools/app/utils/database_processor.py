import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件按SN号分类工具")
        self.root.geometry("600x400")

        self.setup_ui()

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 路径选择区域
        path_frame = ttk.LabelFrame(main_frame, text="选择存储路径", padding="10")
        path_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.path_var, width=60).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(path_frame, text="浏览", command=self.browse_path).grid(row=0, column=1)

        # 文件列表区域
        list_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="10")
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 创建滚动条和列表框
        self.file_listbox = tk.Listbox(list_frame, height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="扫描文件", command=self.scan_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="开始分类", command=self.organize_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="清空列表", command=self.clear_list).pack(side=tk.LEFT)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # 状态标签
        self.status_label = ttk.Label(main_frame, text="请选择存储路径")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(5, 0))

        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            self.status_label.config(text=f"已选择路径: {path}")

    def extract_sn(self, filename):
        """从文件名中提取SN号 - 第一个下划线之前的部分"""
        # 找到第一个下划线的位置
        underscore_pos = filename.find('_')
        if underscore_pos != -1:
            sn = filename[:underscore_pos]
            return sn
        else:
            # 如果没有下划线，尝试使用文件名（不含扩展名）作为SN
            name_without_ext = os.path.splitext(filename)[0]
            return name_without_ext

    def scan_files(self):
        path = self.path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("错误", "请选择有效的存储路径")
            return

        self.file_listbox.delete(0, tk.END)
        self.files = []

        try:
            # 打印调试信息
            print(f"扫描路径: {path}")
            print(f"路径存在: {os.path.exists(path)}")

            # 获取所有文件
            all_files = os.listdir(path)
            print(f"找到 {len(all_files)} 个文件和文件夹")

            # 扫描所有相关文件
            file_count = 0
            for filename in all_files:
                file_path = os.path.join(path, filename)
                # 只处理文件，不处理文件夹
                if os.path.isfile(file_path):
                    # 检查文件扩展名
                    if any(filename.endswith(ext) for ext in ['.zip', '.xlsx', '.json', '.jpg', '.JPG', '.jfif', '.png', 'PNG', 'jpeg']):
                        print(f"找到匹配文件: {filename}")

                        # 使用新的SN提取方法
                        sn = self.extract_sn(filename)
                        if sn:
                            self.files.append(filename)
                            self.file_listbox.insert(tk.END, f"{sn}: {filename}")
                            file_count += 1
                            print(f"成功提取SN号: {sn}")
                        else:
                            print(f"SN号提取失败: {filename}")

            print(f"总共找到 {file_count} 个有效文件")
            self.status_label.config(text=f"找到 {file_count} 个文件")

            if file_count == 0:
                messagebox.showinfo("提示",
                                    "没有找到符合条件的文件。请检查：\n1. 路径是否正确\n2. 文件扩展名是否为.zip/.xlsx/.json/.jpg/.jfif/.png/.jpeg")

        except Exception as e:
            error_msg = f"扫描文件时出错: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)

    def clear_list(self):
        self.file_listbox.delete(0, tk.END)
        self.status_label.config(text="列表已清空")

    def organize_files(self):
        path = self.path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("错误", "请选择有效的存储路径")
            return

        if not hasattr(self, 'files') or not self.files:
            messagebox.showwarning("警告", "没有找到需要分类的文件，请先扫描文件")
            return

        try:
            # 统计SN号
            sn_files = {}
            for file_entry in self.files:
                # 从列表项中提取文件名（去掉前面的SN号）
                filename = file_entry.split(": ", 1)[1] if ": " in file_entry else file_entry

                # 使用新的SN提取方法
                sn = self.extract_sn(filename)
                if sn:
                    if sn not in sn_files:
                        sn_files[sn] = []
                    sn_files[sn].append(filename)
                else:
                    print(f"无法提取SN号: {filename}")

            # 更新进度条
            total_files = sum(len(files) for files in sn_files.values())
            self.progress['maximum'] = total_files
            processed = 0

            # 创建文件夹并移动文件
            moved_files = []
            for sn, files in sn_files.items():
                sn_folder = os.path.join(path, sn)
                os.makedirs(sn_folder, exist_ok=True)

                for filename in files:
                    src_path = os.path.join(path, filename)
                    dst_path = os.path.join(sn_folder, filename)

                    # 检查源文件是否存在
                    if not os.path.exists(src_path):
                        print(f"警告: 源文件不存在 {src_path}")
                        continue

                    # 移动文件
                    shutil.move(src_path, dst_path)
                    moved_files.append(f"{sn}/{filename}")

                    processed += 1
                    self.progress['value'] = processed
                    self.status_label.config(text=f"正在移动文件: {filename}")
                    self.root.update_idletasks()

            # 显示完成信息
            result_message = f"文件分类完成！\n共处理 {len(moved_files)} 个文件\n\n"
            for sn, files in sn_files.items():
                result_message += f"{sn}: {len(files)} 个文件\n"

            # 显示移动的文件列表
            if moved_files:
                result_message += "\n移动的文件:\n" + "\n".join(moved_files[:10])  # 只显示前10个
                if len(moved_files) > 10:
                    result_message += f"\n... 还有 {len(moved_files) - 10} 个文件"

            messagebox.showinfo("完成", result_message)
            self.status_label.config(text=f"分类完成！共处理 {len(moved_files)} 个文件")
            self.progress['value'] = 0

            # 重新扫描文件列表（因为文件已经被移动）
            self.scan_files()

        except Exception as e:
            error_msg = f"分类文件时出错: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
            self.progress['value'] = 0


def main():
    root = tk.Tk()
    app = FileOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
