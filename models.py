"""
质量版本控制系统 - 数据库模型
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()

# 审批等级枚举
class ApprovalLevel(enum.Enum):
    LEVEL_1 = "一级"      # 部门主管
    LEVEL_2 = "二级"      # 质量负责人
    LEVEL_3 = "三级"      # 分管领导
    LEVEL_4 = "四级"      # 质量总监

# 文档状态枚举
class DocStatus(enum.Enum):
    DRAFT = "草稿"
    PENDING = "审批中"
    APPROVED = "已发布"
    REJECTED = "已驳回"
    EXPIRED = "已过期"

# 用户角色
class UserRole(enum.Enum):
    ADMIN = "管理员"
    LEVEL_1_APPROVER = "一级审批人"
    LEVEL_2_APPROVER = "二级审批人"
    LEVEL_3_APPROVER = "三级审批人"
    LEVEL_4_APPROVER = "四级审批人"
    USER = "普通用户"

# 用户表
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100))
    role = db.Column(db.Enum(UserRole), default=UserRole.USER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_approver(self):
        return self.role in [
            UserRole.LEVEL_1_APPROVER,
            UserRole.LEVEL_2_APPROVER,
            UserRole.LEVEL_3_APPROVER,
            UserRole.LEVEL_4_APPROVER,
            UserRole.ADMIN
        ]

# 文档表
class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    doc_type = db.Column(db.String(50))  # 文档类型：制度/流程/表单等
    department = db.Column(db.String(100))  # 所属部门
    version = db.Column(db.String(20), default="1.0")
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))  # COS 文件路径
    file_name = db.Column(db.String(200))  # 原始文件名
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    status = db.Column(db.Enum(DocStatus), default=DocStatus.DRAFT)
    current_level = db.Column(db.Enum(ApprovalLevel), default=ApprovalLevel.LEVEL_1)
    
    # 有效期
    effective_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    
    # 作者
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', backref='documents')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # 版本关联（上一个版本）
    parent_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    parent = db.relationship('Document', remote_side=[id], backref='children')

# 审批记录表
class ApprovalRecord(db.Model):
    __tablename__ = 'approval_records'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    document = db.relationship('Document', backref='approval_records')
    
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approver = db.relationship('User', backref='approvals')
    
    level = db.Column(db.Enum(ApprovalLevel), nullable=False)
    action = db.Column(db.String(20))  # approve/reject
    comment = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 操作日志表
class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='logs')
    
    action = db.Column(db.String(50))  # upload/approve/reject/download/delete
    target_type = db.Column(db.String(50))  # document/user
    target_id = db.Column(db.Integer)
    detail = db.Column(db.Text)  # JSON格式的详细信息
    
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 提醒表
class Reminder(db.Model):
    __tablename__ = 'reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    document = db.relationship('Document', backref='reminders')
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='reminders')
    
    reminder_type = db.Column(db.String(50))  # expiry/approval/custom
    reminder_date = db.Column(db.DateTime, nullable=False)
    message = db.Column(db.Text)
    is_sent = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
