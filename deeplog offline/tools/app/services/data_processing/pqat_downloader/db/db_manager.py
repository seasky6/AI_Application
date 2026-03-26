import sqlite3
from typing import List, Dict, Optional


class LogDBManager:
    def __init__(self, db_path: str = "pqat_logs.db"):
        """初始化数据库管理器"""
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建Radio Unit表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS radio_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT UNIQUE NOT NULL,
                model TEXT,
                platform TEXT,
                issue_description TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建日志文件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radio_unit_id INTEGER NOT NULL,
                log_type INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                FOREIGN KEY (radio_unit_id) REFERENCES radio_units (id)
            )
        ''')

        # 创建下载设置表（用于管理不同问题类型的文件夹）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_type TEXT UNIQUE NOT NULL,
                folder_path TEXT NOT NULL
            )
        ''')

        # 插入默认的问题类型和文件夹路径
        default_settings = [
            ("PA", "pa_issues"),
            ("DC/DC", "dcdc_issues"),
            ("DPD", "dpd_issues"),
            ("SW", "sw_issues"),
            ("TRx", "trx_issues"),
            ("LTU", "ltu_issues"),
            ("FU", "fu_issues"),
            ("Digital", "digital_issues"),
            ("External", "external_issues"),
            ("NFF", "nff_issues"),
            ("Other", "other_issues")
        ]

        for issue_type, folder_path in default_settings:
            try:
                cursor.execute(
                    "INSERT INTO download_settings (issue_type, folder_path) VALUES (?, ?)",
                    (issue_type, folder_path)
                )
            except sqlite3.IntegrityError:
                # 如果已存在则忽略
                pass

        conn.commit()
        conn.close()

    def add_radio_unit(self, serial_number: str, model: str = None, platform: str = None, issue_description: str = None) -> int:
        """添加新的Radio Unit到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO radio_units (serial_number,  model, platform, issue_description) VALUES (?, ?, ?, ?)",
                (serial_number, model, platform, issue_description)
            )
            unit_id = cursor.lastrowid
            conn.commit()
            return unit_id
        except sqlite3.IntegrityError:
            # 如果序列号已存在，则返回现有记录的ID
            cursor.execute(
                "SELECT id FROM radio_units WHERE serial_number = ?",
                (serial_number,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def update_radio_unit(self, serial_number: str, model: str = None, platform: str = None, issue_description: str = None) -> bool:
        """更新Radio Unit信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE radio_units SET model = ?, platform = ?, issue_description = ?, updated_date = CURRENT_TIMESTAMP WHERE serial_number = ?",
            (model, platform, issue_description, serial_number)
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def add_log_file(self, serial_number: str, log_type: int, file_name: str, file_path: str,
                     file_size: int = None, model: str = None, platform: str = None,
                     issue_description: str = None) -> bool:
        """添加日志文件记录到数据库"""
        # 首先确保Radio Unit存在
        unit_id = self.add_radio_unit(serial_number, model, platform, issue_description)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查是否已存在相同文件
        cursor.execute(
            "SELECT id FROM log_files WHERE radio_unit_id = ? AND file_name = ?",
            (unit_id, file_name)
        )

        if cursor.fetchone() is None:
            # 文件不存在，添加新记录
            cursor.execute(
                "INSERT INTO log_files (radio_unit_id, log_type, file_name, file_path, file_size) VALUES (?, ?, ?, ?, ?)",
                (unit_id, log_type, file_name, file_path, file_size)
            )
            conn.commit()
            success = True
        else:
            # 文件已存在
            success = False

        conn.close()
        return success

    def get_radio_unit(self, serial_number: str) -> Optional[Dict]:
        """获取Radio Unit信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, serial_number, model, platform, issue_description, created_date, updated_date FROM radio_units WHERE serial_number = ?",
            (serial_number,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result[0],
                "serial_number": result[1],
                "model": result[2],
                "platform": result[3],
                "issue_description": result[4],
                "created_date": result[5],
                "updated_date": result[6]
            }
        return None

    def get_log_files(self, serial_number: str) -> List[Dict]:
        """获取指定Radio Unit的所有日志文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT lf.id, lf.log_type, lf.file_name, lf.file_path, lf.download_date, lf.file_size
               FROM log_files lf
               JOIN radio_units ru ON lf.radio_unit_id = ru.id
               WHERE ru.serial_number = ?""",
            (serial_number,)
        )

        results = cursor.fetchall()
        conn.close()

        log_files = []
        for result in results:
            log_files.append({
                "id": result[0],
                "log_type": result[1],
                "file_name": result[2],
                "file_path": result[3],
                "download_date": result[4],
                "file_size": result[5]
            })

        return log_files

    def search_radio_units(self, search_term: str) -> List[Dict]:
        """搜索Radio Unit"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, serial_number, model, platform, issue_description, created_date, updated_date
               FROM radio_units
               WHERE serial_number LIKE ? OR model LIKE ? OR platform LIKE ? OR issue_description LIKE ?""",
            (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%")
        )

        results = cursor.fetchall()
        conn.close()

        units = []
        for result in results:
            units.append({
                "id": result[0],
                "serial_number": result[1],
                "model": result[2],
                "platform": result[3],
                "issue_description": result[4],
                "created_date": result[5],
                "updated_date": result[6]
            })

        return units

    def delete_log_file(self, file_id: int) -> bool:
        """删除日志文件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM log_files WHERE id = ?", (file_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return success

    def delete_radio_unit(self, serial_number: str) -> bool:
        """删除Radio Unit及其所有日志文件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 先获取Radio Unit ID
        cursor.execute("SELECT id FROM radio_units WHERE serial_number = ?", (serial_number,))
        result = cursor.fetchone()

        if result:
            unit_id = result[0]
            # 删除相关日志文件记录
            cursor.execute("DELETE FROM log_files WHERE radio_unit_id = ?", (unit_id,))
            # 删除Radio Unit记录
            cursor.execute("DELETE FROM radio_units WHERE id = ?", (unit_id,))
            success = cursor.rowcount > 0
        else:
            success = False

        conn.commit()
        conn.close()
        return success

    def get_download_settings(self) -> List[Dict]:
        """获取所有下载设置（问题类型和文件夹路径）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, issue_type, folder_path FROM download_settings")
        results = cursor.fetchall()
        conn.close()

        settings = []
        for result in results:
            settings.append({
                "id": result[0],
                "issue_type": result[1],
                "folder_path": result[2]
            })

        return settings

    def update_download_setting(self, issue_type: str, folder_path: str) -> bool:
        """更新下载设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE download_settings SET folder_path = ? WHERE issue_type = ?",
            (folder_path, issue_type)
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success


# 全局数据库管理器实例
db_manager = LogDBManager()
