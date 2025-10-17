import os
import configparser
import requests
import pandas as pd
from tkinter import messagebox
from bs4 import BeautifulSoup
from tools.app.services.data_processing.pqat_downloader.db.db_manager import db_manager


#########################################################################################
# authentication and help
#########################################################################################
# 全局变量存储凭据
global_username = None
global_password = None


def get_authRepair(file: str = "/home/hongy19/.pqat_api_rc") -> tuple[str, str]:
    """从配置文件获取维修API(PQAT)的用户名和密码"""
    config = configparser.ConfigParser()
    config.read(file, encoding="utf-8")
    user = config.get("AUTH", 'user1')
    passwd = config.get("AUTH", 'passwd1')
    return user, passwd


def get_authFile() -> tuple[str, str]:
    """获取PQAT Viewer的用户名和密码"""
    if global_username and global_password:
        return global_username, global_password
    else:
        # 如果没有设置全局凭据，抛出异常
        raise RuntimeError("全局凭据未设置，请配置 PQAT Viewer 账户和密码！")


def verify_passwd_pqatviewer(session: requests.Session, serialno: str = "EM8A280070") -> bool:
    """验证PQAT Viewer密码是否正确"""
    print(f"verify_passwd_pqatviewer() - 使用序列号: {serialno}")

    response = get_responseSearch(session, serialno)  # get response, output html response
    print(f"验证响应: {response[:200]}...")  # 只打印前200个字符

    if "Unauthorized" in response:
        print("验证失败 - 未授权")
        return False
    else:
        print("验证成功")
        return True


def verify_passwd_pqatapi(session: requests.Session, user: str, serialno: str = "CN38018936") -> bool:
    """验证PQAT API密码是否正确"""
    data = {
        "login": user,
        "request": "teststation",
        "key" : "basicReturn",
        "serial_no": serialno
        }
    response = get_responseRepaire(session, data)
    response = response.json()
    if isinstance(response, list):
        return True
    else:
        return False


def get_snList(file: str = 'serial_number_list.txt') -> list[str]:
    """从文本文件获取序列号列表"""
    serial_list = []
    with open(file) as f:
        for _ in f:
            tmp = _.strip()
            if tmp:
                serial_list.append(tmp)
    serial_list = list(set(serial_list))  # 去除重复项
    print("序列号列表长度: ", len(serial_list))
    return serial_list


#########################################################################################
# session
#########################################################################################
def get_session(user: str, password: str) -> requests.Session:
    """创建并配置会话"""
    session = requests.Session()
    session.auth = requests.auth.HTTPBasicAuth(user, password)
    session.headers = {
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; "
                          ".NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.3; Tablet PC 2.0)",
            "Authorization": "",
            "Accept-Encoding": "gzip"
        }
    return session


#########################################################################################
# PQAT response
#########################################################################################
def get_responseSearch(session: requests.Session, serialno: str) -> str:
    """获取PQAT Viewer网页响应"""
    url = f'https://common-qtools.sero.wh.rnd.internal.ericsson.com/PQATViewer/?serialno={serialno}'
    try:
        response = session.post(url, timeout=100).content.decode()
    except BaseException:
        print('下载超时，重试中')
    return response


def get_responseFile(session: requests.Session, fileId: str) -> requests.Response:
    """获取文件下载响应"""
    url = 'https://common-qtools.sero.wh.rnd.internal.ericsson.com/PQATViewer/files/{}?download=true'.format(fileId)
    try:
        response = session.get(url, timeout=60)
    except BaseException:
        print('{} 下载超时，重试中'.format(fileId))
    return response


#########################################################################################
# repair response
#########################################################################################
def get_responseRepaire(session: requests.Session, data: dict) -> requests.Response:
    """获取维修API响应"""
    url = "https://rbs-pqat.sero.wh.rnd.internal.ericsson.com"
    mount_point = "/pqat_viewer_api/v0.6_b/api.php"
    url = url + mount_point
    try:
        response = session.post(url, data=data)
    except BaseException:
        print('下载超时，重试中')
    return response


def get_repair(session: requests.Session, snList: list[str], user: str, key: str = "basicReturn") -> pd.DataFrame:
    """获取维修信息"""
    results: list[dict] = []
    for sn in snList:
        data = {
            "login": user,
            "request": "teststation",
            "key": key,
            "serial_no": sn
            }
        response = get_responseRepaire(session, data)
        response = response.json()

        if isinstance(response, list):
            results = results + response
        else:
            print(f"没有搜索到 {sn} 的维修结果")

    return pd.DataFrame(results)


#########################################################################################
# parse idList based on Response
#########################################################################################
def parse_idList1(responseTxt: str) -> pd.DataFrame:
    """解析HTML响应，提取文件ID列表"""
    try:
        # 1. 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(responseTxt, 'html.parser')

        # 2. 查找文件搜索区域 (#filesearch)
        filesearch_div = soup.find('div', id='filesearch')
        if not filesearch_div:
            print("警告: 在HTML中未找到 '#filesearch' 部分")
            return pd.DataFrame()

        # 3. 提取所有缩略图元素 (.thumbnail)
        thumbnails = filesearch_div.find_all(class_='thumbnail')
        if not thumbnails:
            print("警告: 未找到 '.thumbnail' 元素")
            return pd.DataFrame()

        # 4. 分离图片和文本数据
        ids, sns, logs, dates = [], [], [], []
        for element in thumbnails:
            # 处理图片元素 (提取 ID)
            if element.name == 'img' and element.has_attr('id'):
                file_id = element['id'].split('_')[-1]
                ids.append(file_id)

            # 处理文本元素 (提取 SN/Log/Date)
            elif element.name == 'p' and element.has_attr('id'):
                text_parts = element.get_text(separator='\n').split('\n')
                if len(text_parts) >= 3:
                    sns.append(text_parts[0].strip())
                    logs.append(text_parts[1].strip())
                    dates.append(text_parts[2].strip())

        # 5. 检查数据完整性
        if not ids:
            print("警告: 未找到有效的文件ID")
            return pd.DataFrame()

        if len(ids) != len(sns):
            print(f"错误: ID数量 ({len(ids)}) != SN数量 ({len(sns)})")
            return pd.DataFrame()

        # 6. 返回结构化数据
        return pd.DataFrame({
            'id': ids,
            'sn': sns,
            'log': logs,
            'date': pd.to_datetime(dates, errors='coerce')  # 自动转换日期格式
        }).set_index('id')

    except Exception as e:
        print(f"解析HTML时出错: {str(e)}")
        return pd.DataFrame()


#########################################################################################
# filter idList
#########################################################################################
def filter_idList2(idList: pd.DataFrame, logType: int = 0, TimeStrobe: int = 0) -> pd.DataFrame:
    """根据日志类型和时间筛选ID列表.
    snList == [] -> no filter,
    logType: 1 -> ExtLog; 2 -> Site Failure Note; 3 -> proactive; 4 -> HWS Scrap Pictures
    TimeStrobe: -1 -> newest log file; 0 -> download from old to new, till there is a elog in the log file.
    idList                    sn             log       date
    344578067  E23E712241  Proactive Logs 2024-07-05
    344578068  E23E712241  Proactive Logs 2024-07-05
    329780322  CN38018936   Site Failure Note 2024-04-09
    330453196  CN38018936              ExtLog 2024-04-16
    333658970  CN38018936  HWS Scrap Pictures 2024-05-10
    """
    if idList.empty:
        print("filter_idList1中的idList为空")
        return idList

    # 根据日志类型筛选
    if logType == 0:
        pass
    elif logType == 1:  # ExtLog
        idList = idList[idList["log"].str.contains("ExtLog")]
    elif logType == 2:  # Site Failure Note
        idList = idList[idList["log"].str.contains("Site Failure Note")]
    elif logType == 3:  # Proactive Logs
        idList = idList[idList["log"].str.contains("Proactive Logs")]
    elif logType == 4:  # HWS Scrap Pictures
        idList = idList[idList["log"].str.contains("HWS Scrap Pictures")]

        # 根据时间筛选
    if TimeStrobe == 0:
        pass
    elif TimeStrobe == -1:
        idList = idList.iloc[[-1]]
    elif TimeStrobe > 0:
        idList = idList.head(TimeStrobe)
    elif TimeStrobe < -1:
        idList = idList.tail(abs(TimeStrobe))

    return idList


#########################################################################################
# function for download file from PQAT viewer API
#########################################################################################
def add_filename1(response: requests.Response, serialNum: str, outputPath: str) -> str:
    """根据响应生成文件名"""
    fileNameOrigin = response.headers['Content-Disposition'].split("\"")[1]
    return outputPath + '/' + serialNum + '_' + fileNameOrigin


def save_file(response: requests.Response, file_name: str) -> None:
    """保存文件到磁盘"""
    with open(file_name, "wb") as code:
        code.write(response.content)
    return None


def get_filesSN(session: requests.Session, idList: pd.DataFrame,
                outputPath: str = ".", issue_type: str = "未知问题",
                platform: str = "Unknown", model: str = "Unknown") -> None:
    """根据ID列表下载文件, 并记录到数据库"""
    if idList.empty:
        print("PQAT上没有文件")
    else:
        # 获取问题类型对应的文件夹路径
        settings = db_manager.get_download_settings()
        folder_path = outputPath

        # 创建如下目录结构: 平台/型号/SN/问题类型
        for setting in settings:
            if setting["issue_type"] == issue_type:
                first_sn = idList.iloc[0]["sn"]
                folder_path = os.path.join(outputPath, platform, model, setting["folder_path"], first_sn)
                break

        # 确保文件夹存在
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        for fileId in idList.index:
            temp = idList.loc[fileId]
            serialNum = temp["sn"]
            log_type_name = temp["log"]

            # 映射日志类型名称到数字
            log_type_map = {
                "ExtLog": 1,
                "Site Failure Note": 2,
                "Proactive Logs": 3,
                "HWS Scrap Pictures": 4
            }
            log_type = log_type_map.get(log_type_name, 0)

            response = get_responseFile(session, fileId)
            file_name = add_filename1(response, serialNum, folder_path)

            # 检查是否已存在相同文件
            if not os.path.exists(file_name):
                save_file(response, file_name)
                file_size = os.path.getsize(file_name)

                # 记录到数据库
                db_manager.add_log_file(
                    serial_number=serialNum,
                    log_type=log_type,
                    file_name=os.path.basename(file_name),
                    file_path=file_name,
                    file_size=file_size,
                    model=model,
                    platform=platform,
                    issue_description=issue_type
                )

                print(f"序列号: {serialNum}, {file_name} 已下载并记录到数据库!")
            else:
                print(f"文件已存在: {file_name}, 跳过下载")


def get_filesSNList(session: requests.Session,
                    snList: list[str], logType: int = 0, TimeStrobe: int = 0,
                    outputPath: str = ".") -> None:
    """根据序列号列表下载文件"""
    if not snList:
        return

    for serialno in snList:
        print("开始下载序列号: ", serialno)
        response = get_responseSearch(session, serialno)  # get response, output html response
        idList1 = parse_idList1(response)  # parse html response and get id list per sn
        idList2 = filter_idList2(idList1, logType=logType, TimeStrobe=TimeStrobe)  # filter id list
        get_filesSN(session, idList2, outputPath=outputPath)  # download file based on id list and save on disk
    return None


def query_filesSNList(session: requests.Session, snList: list[str]) -> pd.DataFrame:
    """查询序列号列表的文件信息"""
    result = []
    for serialno in snList:
        print("开始查询序列号: ", serialno)
        response = get_responseSearch(session, serialno)  # get response, output html response
        idList1 = parse_idList1(response)  # parse html reponse and get id list per sn
        result.append(idList1)
    return pd.concat(result, axis=0)


def download_file(snFile: str, logType: int = 0, TimeStrobe: int = 0, folder: str = ".") -> None:
    """载日志文件"""
    user, passwd = get_authFile()
    session = get_session(user, passwd)

    if verify_passwd_pqatviewer(session):
        sn_list = get_snList(folder + snFile)
        print(sn_list)
        get_filesSNList(session, sn_list, logType=logType, TimeStrobe=TimeStrobe, outputPath=folder)
    else:
        print("检查密码/用户名")
    return None


def query_file(snFile: str, folder: str = ".") -> pd.DataFrame:
    """查询文件信息"""
    user, passwd = get_authFile()
    session = get_session(user, passwd)
    result = pd.DataFrame()

    if verify_passwd_pqatviewer(session):
        sn_list = get_snList(folder + snFile)
        print(sn_list)
        result = query_filesSNList(session, sn_list)
        print(result)
    else:
        print("检查密码/用户名")

    return result


#########################################################################################
# 新增功能：同时下载多种日志类型
#########################################################################################
def download_multiple_log_types(snFile: str, logTypes=None, TimeStrobe: int = 0, folder: str = ".",
                                issue_type: str = "未知问题", username: str = None, password: str = None,
                                platform: str = 'Unknown', model: str = 'Unknown') -> None:
    """
    同时下载多种日志类型
    Args:
        :param snFile: File containing serial numbers
        :param logTypes: List of log types to download [1, 2, 3, 4] for ExtLog, Site Failure Note, Proactive Logs,
        HWS Scrap Pictures
        :param TimeStrobe: Time selection parameter
        :param folder: Output directory
        :param issue_type: Type of issue for folder organization
        :param username: PQAT username
        :param password: PQAT password
        :param platform: Radio from which platform
        :param model: Radio model number
    """
    print("DEBUG: download_multiple_log_types() 开始执行")
    print(
        f" 参数 - snFile: {snFile}, logTypes: {logTypes}, folder: {folder}, issue_type: {issue_type},"
        f" username: {username}, password: {password}")

    if logTypes is None:
        logTypes = [1, 2, 3, 4]
        print("使用默认日志类型")
    else:
        print("使用用户选择的日志类型")

    print(f"检查凭据 - 传入的用户名: {username}, 密码: {password}")
    print(f"检查凭据 - 全局用户名: {global_username}, 全局密码: {global_password}")

    # 使用提供的凭据或全局凭据
    if username and password:
        user, passwd = username, password
        print("使用传入的凭据")

    elif global_username and global_password:
        user, passwd = global_username, global_password
        print("使用全局凭据")

    else:
        # 尝试从配置文件获取凭据作为后备方案
        try:
            user, passwd = get_authRepair()
            print("使用配置文件中的凭据")
        except:
            print("所有凭据来源都失败")
            messagebox.showerror("错误", "用户名和密码未设置")
            return

    print(f"最终使用的凭据 - 用户: {user}, 密码: {passwd}")

    session = get_session(user, passwd)
    print("创建了会话")

    # 验证密码
    print("开始验证密码")
    if not verify_passwd_pqatviewer(session):
        print("密码验证失败")
        messagebox.showerror("错误", "用户名或密码不正确")
        return
    else:
        print("密码验证成功")

    # 修正文件路径
    sn_file_path = os.path.join(folder, snFile)
    print(f"序列号文件路径: {sn_file_path}")

    sn_list = get_snList(sn_file_path)
    print(f"下载序列号: {sn_list}")
    print(f"日志类型: {logTypes}")

    for serialno in sn_list:
        print(f"处理序列号: {serialno}")
        response = get_responseSearch(session, serialno)
        idList1 = parse_idList1(response)

        if idList1.empty:
            print(f"未找到 {serialno} 的日志")
            continue

        # 为每种日志类型过滤并下载
        for log_type in logTypes:
            print(f"下载 {serialno} 的日志类型 {log_type}")
            idList_filtered = filter_idList2(idList1, logType=log_type, TimeStrobe=TimeStrobe)

            if not idList_filtered.empty:
                get_filesSN(session, idList_filtered, outputPath=folder, issue_type=issue_type, platform=platform,
                            model=model)
            else:
                print(f"未找到 {serialno} 的类型 {log_type} 日志")


if __name__ == '__main__':
    pass
