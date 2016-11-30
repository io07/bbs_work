#encoding: utf-8
from functools import wraps
import json
from flask import g, session, request, make_response, Response, url_for
from flask.blueprints import Blueprint
from flask import render_template, redirect
from flask.ext.wtf import Form
from app import bbs_app
from models import User, Topic, Message
from models import session as sess
from wtforms import StringField, TextAreaField, SubmitField, HiddenField, PasswordField
from wtforms.validators import Required

# views_app = Blueprint('views_app', __name__)

class InputInfo(Form):
    content = TextAreaField('', validators=[Required()])
    submit = SubmitField('Send Enter')

def login_required(func):
    @wraps(func)
    def _decorator(*args, **kwargs):
        if session.has_key('logged_in') and session['logged_in'] == True:
            return func(*args, **kwargs)
        else:
            return redirect('/login/')
    return _decorator

@bbs_app.before_request
def load_user():
    if not session.has_key('user_id'):
        return
    if session['user_id']:
        #print session['user_id']
        user = User.getById(int(session['user_id']))
        if user:
           # print type(user)
           # print user
            g.user = user

@bbs_app.route('/haha', methods=['GET'])
def index_liuwei():
   # print url_for('static', filename='js/Data.js')
    if hasattr(g, 'user') and g.user:
       # print "login"
       # print g.user.__dict__
        return render_template('index.html', user=g.user)
    else:
       # print "no login"
        return redirect('/login/')

@bbs_app.route('/message/list/', methods=['GET'])
@login_required
def message_list():
    q = Message.getByGroupId(g.user.group_id, g.user.id)
    if 'status' in request.args:
        q = q.filter(Message.status==request.args.get('status'))
    if 'desc' in request.args:
        q = q.filter(Message.title.like("%" + request.args.get('desc') + "%"))
    messages = q.order_by(Message.create_time.desc()).all()
    if messages and len(messages) > 0:
        resp = []
        for m in messages:
            res = {}
            res['id'] = m.id
            res['title'] = m.title
            res['author'] = u'无'
            res['create_time'] = str(m.create_time)
            if m.status == 1:
                res['status'] = u'已读'
            else:
                res['status'] = u'未读'
            u = User.getById(m.author_id)
            if u:
                res['author'] = u.name
            resp.append(res)
        return render_template('message_list.html', user=g.user, messages=resp);
    else:
        return render_template('message_list.html', user=g.user)

@bbs_app.route('/message/<int:m_id>/', methods=['GET'])
@login_required
def message_info(m_id):
    m = Message.getById(m_id)
    if not m:
        return render_template('error.html', user=g.user, error='haha')
    if m.user_id != g.user.id and m.group_id != g.user.group_id and m.author_id != g.user.id:
        return render_template('error.html', user=g.user, error='xixi')
    m.status = 1
    sess.commit()
    return render_template('message.html', user=g.user, m=m)

@bbs_app.route('/message/add/', methods=['POST'])
@login_required
def addmessage():
    if g.user.priv != User.TEACHER:
        return render_template('error.html', user=g.user, error=u'haha')
    m = Message()
    m.title = request.form.get('title', None)
    m.desc = request.form.get('content', None)
    m.user_id = request.form.get('user_id', None)
    group_id = request.form.get('group_id', None)
    m.author_id = g.user.id
    m.status = 0
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    group = User.getByGroupId(group_id)
    try:
        for u in group:
            mm = Message()
            mm.title = m.title
            mm.desc = m.desc
            mm.user_id = u.id
            mm.status = 0
            mm.author_id = g.user.id
            sess.add(mm)
        sess.add(m)
        sess.commit()
        resp.data = json.dumps({'code':0, 'msg': u'发布成功'})
    except Exception, ex:
        resp.data = json.dumps({'code': -1, 'reason': ex})
    return resp

@bbs_app.route('/homework/', methods=['GET'])
@login_required
def homework_list():
    works = Homework.getByUserId(g.user.id)
    if works and len(works) > 0:
        return render_template('homework.html', user=g.user, works=works);
    else:
        return render_template('homework.html', user=g.user)

@bbs_app.route('/grade/', methods=['GET'])
@login_required
def grade_list():
    if g.user.priv == 'TEACHER':
        q = Grade.getByTeacherId(g.user.id)
    else: 
        q = Grade.getByUserId(g.user.id)
    subj = request.args.get('subject', None)
    if subj:
        grades = q.filter(Grade.subject.like("%" + subj + "%")).all()
    else:
        grades = q.all()
    return render_template('grade.html', user=g.user, grades=grades)

@bbs_app.route('/grade/data/', methods=['POST'])
@login_required
def get_grade_data(g_id, subject):
    g_id = request.form.get('student_id')
    subject = request.form.get('subject')
    grades = Grade.getByUserId(g_id).filter(Grade.subject==subject).\
            order_by(Grade.contest_time.desc()).all()
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    data = {}
    data_name = []
    data_value = []
    for x in grades:
        data_value.append(x.score)
        data_name.append(x.contest_time)
    data['value'] = data_value
    data['name'] = data_name
    data['title'] = User.getById(g_id).name + u"的" + subject + u"成绩曲线"
    resp.data = data
    return resp

@bbs_app.route('/grade/add/', methods=['POST'])
@login_required
def addgrade():
    if g.user.priv != User.TEACHER:
        return render_template('error.html', user=g.user, error=u'haha')
    m = Grade()
    m.title = request.form.get('subject', None)
    m.contest_time = request.form.get('contest_time', None)
    m.user_id = request.form.get('user_id', None)
    m.teacher_id = g.user.id
    m.semester = request.form.get('semester', None)
    m.score = request.form.get('score', None)
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    try:
        sess.add(m)
        sess.commit()
        resp.data = json.dumps({'code':0, 'msg': u'发布成功'})
    except Exception, ex:
        resp.data = json.dumps({'code': -1, 'reason': ex})
    return resp


