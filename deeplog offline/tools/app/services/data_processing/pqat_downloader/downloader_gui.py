import os.path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tools.app.services.data_processing.pqat_downloader.api.pqat_api import (get_authRepair, get_session, get_snList,
                                                                             get_repair, download_multiple_log_types,
                                                                             verify_passwd_pqatapi)
from tools.app.services.data_processing.pqat_downloader.db.db_manager import db_manager


class PQATDownloaderGUI:
    """PQAT日志下载工具GUI"""
    def __init__(self, default_folder=None, default_sn_file=None):
        """
        初始化PQAT下载器GUI
        Args:
            default_folder: 默认下载文件夹路径
            default_sn_file: 默认序列号文件路径
        """
        self.default_folder = default_folder or self._get_default_folder()
        self.default_sn_file = default_sn_file or self._get_default_sn_file()
        self.root = None

        # 深色主题颜色
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"

    def setup_dark_theme(self, window):
        """设置深色主题"""
        style = ttk.Style()

        # 配置样式
        # 配置黑色文字样式
        style.configure("Black.TEntry",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 黑色文字
        style.configure("Black.TCombobox",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 黑色文字

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)

        # 修改按钮样式 - 黑色字体
        style.configure("TButton",
                        background=self.accent_color,
                        foreground="#000000")  # 黑色字体
        style.map("TButton",
                  background=[("active", self.accent_color),
                              ("pressed", self.accent_color)],
                  foreground=[("active", "#000000"),
                              ("pressed", "#000000")])

        # 配置样式 - 修改为黑色字体
        style.configure("TEntry",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TCombobox",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TListbox",
                        background=self.entry_bg,
                        foreground="#000000")  # 改为黑色字体

        # Treeview 背景保持白色
        style.configure("Treeview",
                        background="#ffffff",  # 白色背景
                        foreground="#000000",  # 黑色字体
                        fieldbackground=self.entry_bg)
        style.configure("Treeview.Heading",
                        background="#f0f0f0",  # 浅灰色表头背景
                        foreground="#000000")  # 黑色头文字

        style.configure("TLabelframe",
                        background=self.bg_color,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TLabelframe.Label",
                        background=self.frame_bg,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab",
                        background=self.frame_bg,
                        foreground="#000000")  # 改为黑色字体
        style.map("TNotebook.Tab",
                  background=[("selected", self.accent_color)])

        # 直接设置窗口背景
        window.configure(bg=self.bg_color)

    @staticmethod
    def _get_default_folder():
        """获取默认文件夹路径"""
        return ("C:\\Users\\ehuabox\\OneDrive - Ericsson\\Desktop\\Works\\AI\\AI for Log Analysis\\deeplog\\"
                "tools\\data\\files_to_be_processed\\")

    @staticmethod
    def _get_default_sn_file():
        """获取默认序列号文件路径"""
        return ("C:\\Users\\ehuabox\\OneDrive - Ericsson\\Desktop\\Works\\AI\\AI for Log Analysis\\deeplog\\"
                "tools\\data\\files_to_be_processed\\SN_List.txt")

    @staticmethod
    def get_repair_summary(snFile: str, folder: str, keys=None) -> None:
        """获取并汇总维修状态信息: key cover basicReturn, productData, fullRepair, repairWithHwlog, RepairSumData"""
        if keys is None:
            keys = ["productData", "basicReturn", "fullRepair", "repairWithHwlog", "RepairSumData"]

        snList = get_snList(folder + snFile)
        print(snList, "\n")
        user, passwd = get_authRepair()
        session = get_session(user, passwd)

        if verify_passwd_pqatapi(session, user):
            for key in keys:
                temp = get_repair(session, snList, user, key=key)
                print(key)
                if key == "fullRepair":
                    columns = ["ComplaintID", "ProductName", "EventDate", "CustomerName", "SerialNo",
                               "MainRepairActionName", "actionDate", "Component", "RepairCodeDescription"]
                    try:
                        temp1 = temp[columns]
                    except KeyError:
                        temp1 = temp
                    print(temp1, "\n")
                else:
                    print(temp, "\n")
                    if key == "productData":
                        temp2 = input("输入回车继续或任意键取消!")
                    if not temp2:
                        temp.to_excel(folder + key + ".xlsx")
                    else:
                        return None
        else:
            print("PQAT API 用户名/密码错误")
        return None

    def create_input_dialog(self, parent):
        """
        创建视窗与用户交互，输入PQAT登录ID及密码，同时决定下载哪种日志
        """

        # 创建模态对话框
        dialog = tk.Toplevel(parent)
        dialog.title("PQAT下载设置")
        dialog.geometry("500x500")
        dialog.transient(parent)
        dialog.grab_set()

        # 设置深色主题
        self.setup_dark_theme(dialog)

        # 创建结果字典
        result = {
            'username': None,
            'password': None,
            'selected_types': [],
            'issue_type': "未知问题",
            'platform': "Unknown",
            'model': "Unknown",
            'confirmed': False
        }

        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 标题标签
        title_label = ttk.Label(main_frame, text="PQAT日志下载设置", font=("Arial", 14, "bold"),
                                foreground=self.fg_color, background=self.bg_color)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 创建选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # 登录凭据框架
        cred_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cred_frame, text="登录凭据")

        # 用户名字段
        username_label = ttk.Label(cred_frame, text="用户名:", font=("Arial", 10), foreground=self.fg_color)
        username_label.grid(row=0, column=0, sticky=tk.W, pady=10)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(cred_frame, textvariable=username_var, width=25, font=("Arial", 10),
                                   style="Black.TEntry")
        username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)

        # 密码字段
        password_label = ttk.Label(cred_frame, text="密码:", font=("Arial", 10), foreground=self.fg_color)
        password_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(cred_frame, textvariable=password_var, show="*", width=25, font=("Arial", 10),
                                   style="Black.TEntry")
        password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)

        # 平台和型号框架
        product_frame = ttk.Frame(notebook, padding="10")
        notebook.add(product_frame, text="产品信息")

        # 平台字段
        platform_label = ttk.Label(product_frame, text="平台:", font=("Arial", 10), foreground=self.fg_color)
        platform_label.grid(row=0, column=0, sticky=tk.W, pady=10)

        # 预定义的平台列表
        platforms = ["Milano", "Stockholm", "Dublin", "Visby", "其它"]
        platform_var = tk.StringVar(value=platforms[0])
        platform_combo = ttk.Combobox(product_frame, textvariable=platform_var, values=platforms, state="readonly",
                                      style="Black.TCombobox")
        platform_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)

        # 型号字段
        model_label = ttk.Label(product_frame, text="型号:", font=("Arial", 10), foreground=self.fg_color)
        model_label.grid(row=1, column=0, sticky=tk.W, pady=10)

        # 预定义的型号列表
        models = ["Radio 2271 B0C", "Radio 2271 B1", "Radio 2271 B28", "Radio 2271 B3", "Radio 2271 B5",
                  "Radio 2271 B7", "Radio 2271 B8", "Radio 4471HP B1", "Radio 4471HP B3", "Radio 4471HP B3B",
                  "Radio 4471HP B7", "Radio 4490 B1B3", "Radio 4490HP B1B3", "Radio 4485 B1B3B7", "Radio 8863 B40"]
        model_var = tk.StringVar(value=models[0])
        model_combo = ttk.Combobox(product_frame, textvariable=model_var, values=models, state="readonly",
                                   style="Black.TCombobox")
        model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)

        # 日志类型选择框架
        log_frame = ttk.Frame(notebook, padding="10")
        notebook.add(log_frame, text="日志类型")

        # 日志类型标题
        log_title_label = ttk.Label(log_frame, text="请选择要下载的日志类型:", font=("Arial", 10, "bold"),
                                    foreground=self.fg_color)
        log_title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # 创建复选框变量
        ext_log_var = tk.IntVar(value=1)
        site_failure_var = tk.IntVar(value=1)
        proactive_var = tk.IntVar(value=1)
        hws_scrap_var = tk.IntVar(value=1)

        # 创建复选框
        ext_log_cb = ttk.Checkbutton(log_frame, text="ExtLog (类型1)", variable=ext_log_var)
        ext_log_cb.grid(row=1, column=0, sticky=tk.W, pady=5)

        site_failure_cb = ttk.Checkbutton(log_frame, text="Site Failure Note (类型2)", variable=site_failure_var)
        site_failure_cb.grid(row=2, column=0, sticky=tk.W, pady=5)

        proactive_cb = ttk.Checkbutton(log_frame, text="Proactive Logs (类型3)", variable=proactive_var)
        proactive_cb.grid(row=3, column=0, sticky=tk.W, pady=5)

        hws_scrap_cb = ttk.Checkbutton(log_frame, text="HWS Scrap Pictures (类型4)", variable=hws_scrap_var)
        hws_scrap_cb.grid(row=4, column=0, sticky=tk.W, pady=5)

        # 在日志类型框架后添加问题类型选择
        issue_frame = ttk.Frame(notebook, padding="10")
        notebook.add(issue_frame, text="问题类型")

        issue_title_label = ttk.Label(issue_frame, text="请选择问题类型:", font=("Arial", 10, "bold"),
                                      foreground=self.fg_color)
        issue_title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # 获取问题类型设置
        settings = db_manager.get_download_settings()
        issue_types = [setting["issue_type"] for setting in settings]

        issue_var = tk.StringVar(value=issue_types[0] if issue_types else "未知问题")
        issue_combo = ttk.Combobox(issue_frame, textvariable=issue_var, values=issue_types, state="readonly",
                                   style="Black.TCombobox")
        issue_combo.grid(row=1, column=0, sticky=tk.W, pady=10, padx=10)

        # 确定按钮点击处理
        def on_ok():
            print("on_ok() 被调用")

            username = username_entry.get()
            password = password_entry.get()
            issue_type = issue_var.get()
            platform = platform_var.get()
            model = model_var.get()

            print(f"用户名: {username}, 密码: {password}, 问题类型: {issue_type}, 平台: {platform}, 型号: {model}")

            if not username or not password:
                print("用户名或密码为空，显示错误消息")
                messagebox.showerror("错误", "用户名和密码不能为空")
                return

            selected_types = []
            if ext_log_var.get() == 1:
                selected_types.append(1)
            if site_failure_var.get() == 1:
                selected_types.append(2)
            if proactive_var.get() == 1:
                selected_types.append(3)
            if hws_scrap_var.get() == 1:
                selected_types.append(4)

            print(f"选择的日志类型: {selected_types}")

            if not selected_types:
                print("没有选择任何日志类型，显示错误消息")
                messagebox.showerror("错误", "请至少选择一种日志类型")
                return

            # 存储结果到result字典
            result['username'] = username
            result['password'] = password
            result['selected_types'] = selected_types
            result['issue_type'] = issue_type
            result['platform'] = platform
            result['model'] = model
            result['confirmed'] = True

            print(f"设置结果 - 用户名: {result['username']}, 密码: {result['password']}")

            # 关闭对话框
            dialog.grab_release()
            dialog.destroy()

        # 取消按钮点击处理
        def on_cancel():
            print("on_cancel() 被调用")
            result['confirmed'] = False
            dialog.grab_release()
            dialog.destroy()

        # 添加确定和取消按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ok_button = ttk.Button(button_frame, text="确定", command=on_ok)
        ok_button.grid(row=0, column=0, padx=10)

        cancel_button = ttk.Button(button_frame, text="取消", command=on_cancel)
        cancel_button.grid(row=0, column=1, padx=10)

        # 配置网格权重以实现调整大小
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        cred_frame.columnconfigure(1, weight=1)
        product_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        # 窗口居中
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry('+{}+{}'.format(x, y))

        # 设置焦点到用户名字段
        username_entry.focus()

        # 等待对话框关闭
        dialog.wait_window(dialog)

        print(
            f"对话框关闭，返回的值 - 用户名: {result['username']}, 密码: {result['password']}, 确认: {result['confirmed']}")

        return result

    def download_logs(self, snFile: str, folder: str, parent_window=None) -> None:
        """
        从PQAT下载日志文件的主函数

        Args:
            snFile: 序列号文件名
            folder: 下载文件夹路径
            parent_window: 父窗口，如果为None则使用self.root
        """
        print("download_logs() 开始执行")

        if parent_window is None:
            parent_window = self.root

        # 获取用户凭据、日志类型选择和问题类型
        result = self.create_input_dialog(parent_window)

        print(f"从对话框返回的值 - 用户名: {result['username']}, 密码: {result['password']},"
              f" 日志类型: {result['selected_types']}, 问题类型: {result['issue_type']},"
              f" 平台: {result['platform']}, 型号: {result['model']}, 确认: {result['confirmed']}")

        if not result['confirmed']:
            print("用户取消了操作")
            return None

        # 下载多种日志类型
        print(
            f"调用download_multiple_log_types() - 日志类型: {result['selected_types']}, 问题类型: {result['issue_type']}")
        try:
            download_multiple_log_types(
                snFile=snFile,
                logTypes=result['selected_types'],
                TimeStrobe=0,
                folder=folder,
                issue_type=result['issue_type'],
                username=result['username'],
                password=result['password'],
                platform=result['platform'],
                model=result['model']
            )
            print("下载完成")
            messagebox.showinfo("完成", "日志下载完成")
        except Exception as e:
            print(f"下载过程中出错: {str(e)}")
            messagebox.showerror("错误", f"下载过程中出错: {str(e)}")

        return None

    def manage_database(self):
        """数据库管理界面"""
        management_window = tk.Toplevel(self.root)
        management_window.title("PQAT日志数据库管理")
        management_window.geometry("1000x700")

        # 设置深色主题
        self.setup_dark_theme(management_window)

        # 创建选项卡
        notebook = ttk.Notebook(management_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 搜索选项卡
        search_frame = ttk.Frame(notebook, padding="10")
        notebook.add(search_frame, text="搜索")

        search_label = ttk.Label(search_frame, text="搜索关键词:", foreground=self.fg_color)
        search_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30, style="Black.TEntry")
        search_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # 先定义所有需要的函数
        def perform_search(search_term):
            """执行搜索并更新结果"""
            # 清空现有结果
            for item in search_tree.get_children():
                search_tree.delete(item)

            results = db_manager.search_radio_units(search_term)
            for result in results:
                search_tree.insert("", "end", values=(
                    result["serial_number"],
                    result["model"] or "",
                    result["platform"] or "",
                    result["issue_description"] or "",
                    result["created_date"]
                ))

        def on_unit_select(event):
            """当选择Radio Unit时显示其日志文件和详细信息"""
            selection = search_tree.selection()
            if selection:
                item = search_tree.item(selection[0])
                serial_number = item["values"][0]

                # 更新编辑框中的信息
                unit_info = db_manager.get_radio_unit(serial_number)
                if unit_info:
                    model_var.set(unit_info.get("model", ""))
                    platform_var.set(unit_info.get("platform", ""))
                    issue_var.set(unit_info.get("issue_description", ""))

                # 清空现有日志文件
                for item in log_tree.get_children():
                    log_tree.delete(item)

                log_files = db_manager.get_log_files(serial_number)
                for log_file in log_files:
                    log_type_map = {
                        1: "ExtLog",
                        2: "Site Failure Note",
                        3: "Proactive Logs",
                        4: "HWS Scrap Pictures"
                    }
                    log_type_name = log_type_map.get(log_file["log_type"], "未知")

                    log_tree.insert("", "end", values=(
                        log_type_name,
                        log_file["file_name"],
                        log_file["download_date"],
                        f"{log_file['file_size']} bytes" if log_file["file_size"] else "未知"
                    ))

        def update_unit_info():
            """更新Radio Unit信息"""
            selection = search_tree.selection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个Radio Unit")
                return

            item = search_tree.item(selection[0])
            serial_number = item["values"][0]

            success = db_manager.update_radio_unit(
                serial_number=serial_number,
                model=model_var.get(),
                platform=platform_var.get(),
                issue_description=issue_var.get()
            )

            if success:
                messagebox.showinfo("成功", "信息更新成功")
                perform_search(search_var.get())  # 刷新搜索结果
            else:
                messagebox.showerror("错误", "信息更新失败")

        # 搜索按钮
        search_button = ttk.Button(search_frame, text="搜索", command=lambda: perform_search(search_var.get()))
        search_button.grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)

        # 搜索结果列表
        search_results_frame = ttk.Frame(search_frame)
        search_results_frame.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, pady=10)

        # 添加平台、型号和问题描述列
        columns = ("serial_number", "model", "platform", "issue_description", "created_date")
        search_tree = ttk.Treeview(search_results_frame, columns=columns, show="headings")

        search_tree.heading("serial_number", text="序列号")
        search_tree.heading("model", text="型号")
        search_tree.heading("platform", text="平台")
        search_tree.heading("issue_description", text="问题描述")
        search_tree.heading("created_date", text="创建日期")

        search_tree.column("serial_number", width=120)
        search_tree.column("model", width=100)
        search_tree.column("platform", width=100)
        search_tree.column("issue_description", width=200)
        search_tree.column("created_date", width=120)

        scrollbar = ttk.Scrollbar(search_results_frame, orient=tk.VERTICAL, command=search_tree.yview)
        search_tree.configure(yscrollcommand=scrollbar.set)

        search_tree.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # 日志文件列表
        log_files_frame = ttk.Frame(search_frame)
        log_files_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW, pady=10)

        log_columns = ("log_type", "file_name", "download_date", "file_size")
        log_tree = ttk.Treeview(log_files_frame, columns=log_columns, show="headings")

        log_tree.heading("log_type", text="日志类型")
        log_tree.heading("file_name", text="文件名")
        log_tree.heading("download_date", text="下载日期")
        log_tree.heading("file_size", text="文件大小")

        log_tree.column("log_type", width=100)
        log_tree.column("file_name", width=200)
        log_tree.column("download_date", width=120)
        log_tree.column("file_size", width=80)

        log_scrollbar = ttk.Scrollbar(log_files_frame, orient=tk.VERTICAL, command=log_tree.yview)
        log_tree.configure(yscrollcommand=log_scrollbar.set)

        log_tree.grid(row=0, column=0, sticky=tk.NSEW)
        log_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # 编辑框架
        edit_frame = ttk.Frame(search_frame)
        edit_frame.grid(row=3, column=0, columnspan=3, sticky=tk.NSEW, pady=10)

        # 型号编辑
        model_label = ttk.Label(edit_frame, text="型号:", foreground=self.fg_color)
        model_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        model_var = tk.StringVar()
        model_entry = ttk.Entry(edit_frame, textvariable=model_var, width=20)
        model_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # 平台编辑
        platform_label = ttk.Label(edit_frame, text="平台:", foreground=self.fg_color)
        platform_label.grid(row=0, column=2, sticky=tk.W, pady=5)

        platform_var = tk.StringVar()
        platform_combo = ttk.Combobox(edit_frame, textvariable=platform_var,
                                      values=["Milano", "Stockholm", "Dublin", "其他"],
                                      state="readonly", width=15)
        platform_combo.grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)

        # 问题描述编辑
        issue_label = ttk.Label(edit_frame, text="问题描述:", foreground=self.fg_color)
        issue_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        issue_var = tk.StringVar()
        issue_entry = ttk.Entry(edit_frame, textvariable=issue_var, width=50)
        issue_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=5, padx=5)

        # 更新按钮
        update_button = ttk.Button(edit_frame, text="更新信息", command=update_unit_info)
        update_button.grid(row=2, column=0, columnspan=4, pady=10)

        # 设置选项卡
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="设置")

        settings_label = ttk.Label(settings_frame, text="下载路径设置:", font=("Arial", 10, "bold"), foreground=self.fg_color)
        settings_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        settings = db_manager.get_download_settings()
        for i, setting in enumerate(settings):
            ttk.Label(settings_frame, text=setting["issue_type"] + ":").grid(row=i + 1, column=0, sticky=tk.W, pady=5)
            path_var = tk.StringVar(value=setting["folder_path"])
            path_entry = ttk.Entry(settings_frame, textvariable=path_var, width=30)
            path_entry.grid(row=i + 1, column=1, sticky=tk.W, pady=5, padx=5)

            save_button = ttk.Button(settings_frame, text="保存",
                                     command=lambda it=setting["issue_type"], pv=path_var:
                                     db_manager.update_download_setting(it, pv.get()))
            save_button.grid(row=i + 1, column=2, sticky=tk.W, pady=5, padx=5)

        # 绑定事件
        search_tree.bind("<<TreeviewSelect>>", on_unit_select)

        # 配置权重
        search_frame.columnconfigure(0, weight=1)
        search_frame.rowconfigure(1, weight=1)
        search_frame.rowconfigure(2, weight=1)
        search_frame.rowconfigure(3, weight=1)
        search_results_frame.columnconfigure(0, weight=1)
        search_results_frame.rowconfigure(0, weight=1)
        log_files_frame.columnconfigure(0, weight=1)
        log_files_frame.rowconfigure(0, weight=1)

        # 初始搜索所有记录
        perform_search("")

    @staticmethod
    def _browse_folder(folder_var):
        """浏览文件夹"""
        folder_path = filedialog.askdirectory(initialdir=folder_var.get())
        if folder_path:
            folder_var.set(folder_path)

    @staticmethod
    def _browse_snfile(snfile_var):
        """浏览序列号文件"""
        file_path = filedialog.askopenfilename(
            initialdir=os.path.dirname(snfile_var.get()) or ".",
            title="选择序列号文件",
            filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*"))
        )
        if file_path:
            snfile_var.set(file_path)

    def run(self):
        """运行PQAT下载器GUI"""
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("PQAT日志下载管理")
        self.root.geometry("600x400")

        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 添加标题
        title_label = ttk.Label(main_frame, text="PQAT日志下载管理", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # 添加配置框架
        config_frame = ttk.LabelFrame(main_frame, text="配置设置", padding="10")
        config_frame.pack(fill=tk.X, pady=10)

        # 下载路径配置
        folder_label = ttk.Label(config_frame, text="下载路径:")
        folder_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        folder_var = tk.StringVar(value=self.default_folder)
        folder_entry = ttk.Entry(config_frame, textvariable=folder_var, width=50)
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        folder_button = ttk.Button(config_frame, text="浏览", command=lambda: self._browse_folder(folder_var))
        folder_button.grid(row=0, column=2, pady=5, padx=5)

        # 序列号文件配置
        snfile_label = ttk.Label(config_frame, text="序列号文件:")
        snfile_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        snfile_var = tk.StringVar(value=self.default_sn_file)
        snfile_entry = ttk.Entry(config_frame, textvariable=snfile_var, width=50)
        snfile_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        snfile_button = ttk.Button(config_frame, text="浏览", command=lambda: self._browse_snfile(snfile_var))
        snfile_button.grid(row=1, column=2, pady=5, padx=5)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20, fill=tk.X)  # 添加 fill=tk.X 使框架填满宽度

        # 添加下载按钮
        download_button = ttk.Button(button_frame, text="下载日志",
                                     command=lambda: self.download_logs(snfile_var.get(), folder_var.get()))
        download_button.pack(side=tk.LEFT, padx=10, expand=True)  # 改为 pack 布局

        # 添加管理按钮
        manage_button = ttk.Button(button_frame, text="管理数据库",
                                   command=self.manage_database)
        manage_button.pack(side=tk.LEFT, padx=10, expand=True)  # 改为 pack 布局

        # 添加退出按钮
        exit_button = ttk.Button(button_frame, text="退出", command=self.root.quit)
        exit_button.pack(side=tk.LEFT, padx=10, expand=True)  # 改为 pack 布局

        # 配置权重
        config_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        # 启动主循环
        self.root.mainloop()


# 使用示例
if __name__ == "__main__":
    # 创建下载器实例并运行
    downloader = PQATDownloaderGUI()
    downloader.run()
