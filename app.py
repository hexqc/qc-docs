"""
质量版本控制系统 - Flask 主程序
"""
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models import db, User, Document, ApprovalRecord, OperationLog, Reminder, DocStatus, ApprovalLevel, UserRole
import json

# 加载环境变量
load_dotenv()

# 创建应用
app = Flask(__name__, static_folder='static')

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///qc_docs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CORS
CORS(app)

# 数据库
db.init_app(app)

# 登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== 用户认证 ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'real_name': user.real_name,
                'role': user.role.value,
                'department': user.department
            }
        })
    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    logout_user()
    return jsonify({'success': True})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'real_name': current_user.real_name,
        'role': current_user.role.value,
        'department': current_user.department
    })

# ==================== 文档管理 ====================

@app.route('/api/documents', methods=['GET'])
@login_required
def get_documents():
    """获取文档列表"""
    status = request.args.get('status')
    department = request.args.get('department')
    
    query = Document.query
    if status:
        query = query.filter_by(status=DocStatus(status))
    if department:
        query = query.filter_by(department=department)
    
    documents = query.order_by(Document.updated_at.desc()).all()
    return jsonify([{
        'id': doc.id,
        'title': doc.title,
        'doc_type': doc.doc_type,
        'department': doc.department,
        'version': doc.version,
        'status': doc.status.value,
        'author': doc.author.real_name if doc.author else '未知',
        'created_at': doc.created_at.isoformat(),
        'updated_at': doc.updated_at.isoformat(),
        'effective_date': doc.effective_date.isoformat() if doc.effective_date else None,
        'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None
    } for doc in documents])

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    """获取单个文档详情"""
    doc = Document.query.get_or_404(doc_id)
    return jsonify({
        'id': doc.id,
        'title': doc.title,
        'doc_type': doc.doc_type,
        'department': doc.department,
        'version': doc.version,
        'description': doc.description,
        'file_name': doc.file_name,
        'file_size': doc.file_size,
        'status': doc.status.value,
        'current_level': doc.current_level.value,
        'author': doc.author.real_name if doc.author else '未知',
        'author_id': doc.author_id,
        'created_at': doc.created_at.isoformat(),
        'updated_at': doc.updated_at.isoformat(),
        'effective_date': doc.effective_date.isoformat() if doc.effective_date else None,
        'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
        'approval_records': [{
            'level': r.level.value,
            'approver': r.approver.real_name,
            'action': r.action,
            'comment': r.comment,
            'created_at': r.created_at.isoformat()
        } for r in doc.approval_records]
    })

@app.route('/api/documents', methods=['POST'])
@login_required
def create_document():
    """创建文档（上传文件）"""
    data = request.json
    doc = Document(
        title=data['title'],
        doc_type=data.get('doc_type'),
        department=data.get('department'),
        version=data.get('version', '1.0'),
        description=data.get('description'),
        author_id=current_user.id,
        status=DocStatus.DRAFT
    )
    db.session.add(doc)
    
    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action='upload',
        target_type='document',
        target_id=doc.id,
        detail=json.dumps({'title': doc.title})
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'success': True, 'id': doc.id})

@app.route('/api/documents/<int:doc_id>', methods=['PUT'])
@login_required
def update_document(doc_id):
    """更新文档"""
    doc = Document.query.get_or_404(doc_id)
    data = request.json
    
    if doc.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': '无权限修改'}), 403
    
    doc.title = data.get('title', doc.title)
    doc.doc_type = data.get('doc_type', doc.doc_type)
    doc.department = data.get('department', doc.department)
    doc.description = data.get('description', doc.description)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    """删除文档"""
    doc = Document.query.get_or_404(doc_id)
    
    if doc.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': '无权限删除'}), 403
    
    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action='delete',
        target_type='document',
        target_id=doc.id,
        detail=json.dumps({'title': doc.title})
    )
    db.session.add(log)
    db.session.delete(doc)
    db.session.commit()
    
    return jsonify({'success': True})

# ==================== 审批流程 ====================

@app.route('/api/documents/<int:doc_id>/submit', methods=['POST'])
@login_required
def submit_for_approval(doc_id):
    """提交审批"""
    doc = Document.query.get_or_404(doc_id)
    
    if doc.author_id != current_user.id:
        return jsonify({'success': False, 'message': '只能提交自己的文档'}), 403
    
    if doc.status != DocStatus.DRAFT:
        return jsonify({'success': False, 'message': '只有草稿状态才能提交'}), 400
    
    doc.status = DocStatus.PENDING
    doc.current_level = ApprovalLevel.LEVEL_1
    
    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action='submit_approval',
        target_type='document',
        target_id=doc.id,
        detail=json.dumps({'title': doc.title})
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/documents/<int:doc_id>/approve', methods=['POST'])
@login_required
def approve_document(doc_id):
    """审批通过"""
    doc = Document.query.get_or_404(doc_id)
    data = request.json
    comment = data.get('comment', '')
    
    # 检查权限
    level_role_map = {
        ApprovalLevel.LEVEL_1: UserRole.LEVEL_1_APPROVER,
        ApprovalLevel.LEVEL_2: UserRole.LEVEL_2_APPROVER,
        ApprovalLevel.LEVEL_3: UserRole.LEVEL_3_APPROVER,
        ApprovalLevel.LEVEL_4: UserRole.LEVEL_4_APPROVER,
    }
    
    required_role = level_role_map.get(doc.current_level)
    if current_user.role != required_role and current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': '无权限审批此级别'}), 403
    
    # 记录审批
    record = ApprovalRecord(
        document_id=doc_id,
        approver_id=current_user.id,
        level=doc.current_level,
        action='approve',
        comment=comment
    )
    db.session.add(record)
    
    # 更新状态
    if doc.current_level == ApprovalLevel.LEVEL_4:
        # 四级审批完成，文档发布
        doc.status = DocStatus.APPROVED
        doc.published_at = datetime.utcnow()
    else:
        # 进入下一级审批
        level_order = [ApprovalLevel.LEVEL_1, ApprovalLevel.LEVEL_2, ApprovalLevel.LEVEL_3, ApprovalLevel.LEVEL_4]
        next_index = level_order.index(doc.current_level) + 1
        doc.current_level = level_order[next_index]
    
    db.session.commit()
    return jsonify({'success': True, 'status': doc.status.value})

@app.route('/api/documents/<int:doc_id>/reject', methods=['POST'])
@login_required
def reject_document(doc_id):
    """审批驳回"""
    doc = Document.query.get_or_404(doc_id)
    data = request.json
    comment = data.get('comment', '')
    
    if not comment:
        return jsonify({'success': False, 'message': '驳回必须填写原因'}), 400
    
    # 记录审批
    record = ApprovalRecord(
        document_id=doc_id,
        approver_id=current_user.id,
        level=doc.current_level,
        action='reject',
        comment=comment
    )
    db.session.add(record)
    
    doc.status = DocStatus.REJECTED
    db.session.commit()
    
    return jsonify({'success': True})

# ==================== 待办事项 ====================

@app.route('/api/pending', methods=['GET'])
@login_required
def get_pending_approvals():
    """获取待审批文档"""
    # 根据用户角色获取对应级别的待审批文档
    level_role_map = {
        UserRole.LEVEL_1_APPROVER: ApprovalLevel.LEVEL_1,
        UserRole.LEVEL_2_APPROVER: ApprovalLevel.LEVEL_2,
        UserRole.LEVEL_3_APPROVER: ApprovalLevel.LEVEL_3,
        UserRole.LEVEL_4_APPROVER: ApprovalLevel.LEVEL_4,
    }
    
    if current_user.role == UserRole.ADMIN:
        # 管理员获取所有待审批
        pending_docs = Document.query.filter_by(status=DocStatus.PENDING).all()
    else:
        level = level_role_map.get(current_user.role)
        if not level:
            return jsonify([])
        pending_docs = Document.query.filter_by(status=DocStatus.PENDING, current_level=level).all()
    
    return jsonify([{
        'id': doc.id,
        'title': doc.title,
        'department': doc.department,
        'current_level': doc.current_level.value,
        'author': doc.author.real_name if doc.author else '未知',
        'created_at': doc.created_at.isoformat()
    } for doc in pending_docs])

# ==================== 统计面板 ====================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """获取统计数据"""
    total = Document.query.count()
    pending = Document.query.filter_by(status=DocStatus.PENDING).count()
    approved = Document.query.filter_by(status=DocStatus.APPROVED).count()
    rejected = Document.query.filter_by(status=DocStatus.REJECTED).count()
    
    # 即将过期文档（30天内）
    soon_expired = Document.query.filter(
        Document.expiry_date != None,
        Document.expiry_date <= datetime.utcnow().date() + timedelta(days=30),
        Document.expiry_date > datetime.utcnow().date()
    ).count()
    
    return jsonify({
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'soon_expired': soon_expired
    })

# ==================== 用户管理（管理员） ====================

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """获取用户列表"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': '无权限'}), 403
    
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'real_name': u.real_name,
        'department': u.department,
        'role': u.role.value,
        'is_active': u.is_active,
        'last_login': u.last_login.isoformat() if u.last_login else None
    } for u in users])

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    """创建用户"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': '无权限'}), 403
    
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    
    user = User(
        username=data['username'],
        real_name=data['real_name'],
        department=data.get('department'),
        role=UserRole(data.get('role', 'USER'))
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True, 'id': user.id})

# ==================== 初始化 ====================

def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 创建管理员账号
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                real_name='系统管理员',
                role=UserRole.ADMIN
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            
            # 创建各级审批人示例账号
            approvers = [
                ('hanzg', '韩志刚', UserRole.LEVEL_1_APPROVER, '部门主管'),
                ('wangxl', '王晓丽', UserRole.LEVEL_2_APPROVER, '质量负责人'),
                ('lim', '李明', UserRole.LEVEL_3_APPROVER, '分管领导'),
                ('zhangzj', '张总监', UserRole.LEVEL_4_APPROVER, '质量总监'),
            ]
            for username, real_name, role, dept in approvers:
                user = User(username=username, real_name=real_name, role=role, department=dept)
                user.set_password('Qc@123')
                db.session.add(user)
            
            db.session.commit()
            print("初始化完成：管理员账号 admin/Admin@123")

# ==================== 前端路由 ====================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """服务前端页面"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.before_request
def ensure_db_init():
    """首次请求时自动初始化数据库"""
    if not hasattr(app, '_db_initialized'):
        try:
            with app.app_context():
                init_db()
            app._db_initialized = True
        except Exception as e:
            print(f"DB init error: {e}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
