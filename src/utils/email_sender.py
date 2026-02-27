"""
邮件发送模块

支持通过SMTP发送每日新闻报告邮件
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logger import log


class EmailSender:
    """
    邮件发送器

    通过SMTP发送每日新闻报告
    """

    def __init__(self, config: dict):
        """
        初始化邮件发送器

        Args:
            config: 邮件配置字典，包含:
                - smtp_server: SMTP服务器地址
                - smtp_port: SMTP端口
                - username: 发件人邮箱
                - password: 邮箱授权码
                - recipients: 收件人列表
                - use_ssl: 是否使用SSL (默认True)
        """
        self.smtp_server = config.get("smtp_server", "smtp.qq.com")
        self.smtp_port = config.get("smtp_port", 465)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.recipients = config.get("recipients", [])
        self.use_ssl = config.get("use_ssl", True)

    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        将Markdown文本转换为简单的HTML格式

        Args:
            markdown_text: Markdown格式文本

        Returns:
            HTML格式文本
        """
        lines = markdown_text.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()

            # 标题
            if stripped.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f'<h1 style="color:#1a1a2e;border-bottom:2px solid #e94560;padding-bottom:8px;">{stripped[2:]}</h1>')
            elif stripped.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f'<h2 style="color:#16213e;margin-top:20px;">{stripped[3:]}</h2>')
            elif stripped.startswith("### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f'<h3 style="color:#0f3460;">{stripped[4:]}</h3>')
            # 列表项
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    html_lines.append('<ul style="line-height:1.8;">')
                    in_list = True
                content = stripped[2:]
                # 处理链接 [text](url)
                import re
                content = re.sub(
                    r'\[([^\]]+)\]\(([^)]+)\)',
                    r'<a href="\2" style="color:#e94560;">\1</a>',
                    content
                )
                # 处理加粗 **text**
                content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
                html_lines.append(f"<li>{content}</li>")
            # 分隔线
            elif stripped.startswith("---"):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append('<hr style="border:1px solid #eee;margin:15px 0;">')
            # 空行
            elif not stripped:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("<br>")
            # 普通段落
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                import re
                content = stripped
                content = re.sub(
                    r'\[([^\]]+)\]\(([^)]+)\)',
                    r'<a href="\2" style="color:#e94560;">\1</a>',
                    content
                )
                content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
                html_lines.append(f'<p style="line-height:1.8;color:#333;">{content}</p>')

        if in_list:
            html_lines.append("</ul>")

        body = "\n".join(html_lines)

        return f"""
        <div style="max-width:700px;margin:0 auto;padding:20px;font-family:'Microsoft YaHei','Helvetica Neue',Arial,sans-serif;background:#fafafa;">
            <div style="background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.08);">
                {body}
            </div>
            <div style="text-align:center;margin-top:20px;color:#999;font-size:12px;">
                <p>此邮件由 AI日报系统 自动发送</p>
            </div>
        </div>
        """

    def send_report(
        self,
        report_path: str,
        date: Optional[datetime] = None
    ) -> bool:
        """
        发送报告邮件

        Args:
            report_path: 报告文件路径
            date: 日期（用于邮件标题）

        Returns:
            是否发送成功
        """
        if not self.username or not self.password:
            log.warning("邮件发送未配置发件人信息，跳过发送")
            return False

        if not self.recipients:
            log.warning("邮件发送未配置收件人，跳过发送")
            return False

        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")

        # 读取报告内容
        report_file = Path(report_path)
        if not report_file.exists():
            log.error(f"报告文件不存在: {report_path}")
            return False

        report_content = report_file.read_text(encoding="utf-8")

        # 构建邮件
        subject = f"AI行业日报 - {date_str}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = ", ".join(self.recipients)

        # 纯文本版本
        text_part = MIMEText(report_content, "plain", "utf-8")
        msg.attach(text_part)

        # HTML版本
        html_content = self._markdown_to_html(report_content)
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # 发送邮件
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_server, self.smtp_port, context=context
                ) as server:
                    server.login(self.username, self.password)
                    server.sendmail(
                        self.username,
                        self.recipients,
                        msg.as_string()
                    )
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.sendmail(
                        self.username,
                        self.recipients,
                        msg.as_string()
                    )

            log.info(f"邮件发送成功: {subject} -> {', '.join(self.recipients)}")
            return True

        except smtplib.SMTPAuthenticationError:
            log.error("邮件发送失败：SMTP认证失败，请检查邮箱和授权码")
            return False
        except smtplib.SMTPException as e:
            log.error(f"邮件发送失败：SMTP错误 - {e}")
            return False
        except Exception as e:
            log.error(f"邮件发送失败: {e}")
            return False
