from flask import Flask,render_template,request,session,redirect,flash,get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timedelta
import json
import os
import math
from werkzeug.utils import secure_filename
from flask_mail import Mail

with open("config.json","r") as c:
    params=json.load(c)["params"]
    
app=Flask(__name__)
app.secret_key = 'secret-key'
app.config['UPLOAD_FOLDER'] = params["upload_location"]
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_USE_SSL = True,
    MAIL_PORT = '465',
    MAIL_USERNAME = params["gmail-user"],
    MAIL_PASSWORD = params["gmail-password"]
)
mail=Mail(app)

if params['local_server']:
    app.config['SQLALCHEMY_DATABASE_URI']= params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI']=params['prod_uri']
db=SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)  #Variables are as same as in database name contact
    name = db.Column(db.String(50),nullable=False)   ##EQn-1
    email = db.Column(db.String(50), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(12), nullable=False)

    def __init__(self,name,email,phone_num,msg,date):
        self.name=name
        self.email=email
        self.phone_num=phone_num
        self.msg=msg
        self.date=date

class Posts(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    Title=db.Column(db.String(100),unique=True,nullable=False)
    Subheading=db.Column(db.String(50),unique=False,nullable=True)
    slug=db.Column(db.String(30),unique=True,nullable=False)
    Content=db.Column(db.String(1000),unique=False,nullable=False)
    url=db.Column(db.String(512),unique=False,nullable=True)
    img_file=db.Column(db.String(100),unique=False,nullable=True)
    post_by=db.Column(db.String(20),unique=False,nullable=True)
    Date = db.Column(db.String(12), nullable=False)

    def __init__(self,Title,Subheading,slug,Content,url,img_file,post_by,Date):
        self.Title=Title
        self.Subheading=Subheading
        self.slug=slug
        self.Content=Content
        self.url=url
        self.img_file=img_file
        self.post_by=post_by
        self.Date=Date

@app.route("/")
def Home():
    posts=Posts.query.filter_by().all()
    # [0:params["no_of_posts"]]
    last=math.ceil(len(posts)/int(params["no_of_posts"]))
    page=request.args.get('page')

    if not str(page).isnumeric():
        page=1
    page=int(page)
    post=posts[(page-1)*int(params["no_of_posts"]):(page-1)*int(params["no_of_posts"])+int(params["no_of_posts"])]

    f=False
    l=False
    if page==1:
        prev="#"
        next="/?page="+str(page+1)
        f=True
        l=False
    elif page==last:
        prev="/?page="+str(page-1)
        next="#"
        f=False
        l=False
    else:
        prev="/?page="+str(page-1)
        next="/?page="+str(page+1)
        f=False
        l=True
        
    return render_template('index.html',params=params,post=post,prev=prev,next=next,f=f,l=l)

@app.route("/about")
def about():
    return render_template('about.html',params=params)

@app.route("/dashboard",methods = ['GET','POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_user']:
        return render_template('dashboard.html',params=params)
    error = None
    if request.method=='POST':
        username=request.form.get('uname')
        password=request.form.get('password')

        if username==params["admin_user"] and password==params['admin_password']:
            session['user']=username
            flash(params['login_success_msg'])
            return render_template('dashboard.html',params=params)
        else:
            error=params['login_err_msg']
            return render_template('login.html',params=params,error=error)
        
    return render_template('login.html',params=params)

@app.before_request
def make_session_permanent():
    session.permanent=True
    app.permanent_session_lifetime=timedelta(minutes=15)

@app.route('/logout')
def logout():
    session.pop('user')
    flash("Logged out Successfully!","success")
    return redirect('/dashboard')

@app.route("/ved",methods = ['GET'])
def ved():
    if 'user' in session and session['user'] == params['admin_user']:
        posts=Posts.query.all()
        return render_template('View-Edit-Delete.html',params=params,posts=posts)
    

@app.route("/add/<string:post_sno>",methods = ['GET','POST'])
def add(post_sno):
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            Name=params['admin_user']
            title=request.form.get('title')
            Subtitle=request.form.get('subtitle')
            Content=request.form.get('content')
            Url=request.form.get('link')
            Img_name=request.form.get('img_name')

            if post_sno==0:
                post=Posts(Title=title,Subheading=Subtitle,slug="-".join(title.split(" ")),Content=Content,url=Url,img_file=Img_name,post_by=Name,Date=datetime.now())
                db.session.add(post)
                db.session.commit()
                return redirect('/ved')

            else:
                post = Posts.query.filter_by(sno=post_sno).first()
                post.Title=title
                post.slug="-".join(title.split(" "))
                post.Subheading=Subtitle
                post.Content=Content
                post.url=Url
                post.img_file=Img_name
                post.post_by=Name
                db.session.commit()
                return redirect('/add/'+post_sno)
        post=Posts.query.filter_by(sno=post_sno).first()
        return render_template('Add.html',params=params,post=post)

@app.route('/delete/<string:post_sno>',methods=['GET','POST'])
def delete(post_sno):
    if 'user' in session and session['user']==params['admin_user']:
        post=Posts.query.filter_by(sno=post_sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/ved')
    
@app.route("/post/<string:post_slug>",methods = ['GET'])
def post_route(post_slug):
    post=Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html',params=params,post=post)

@app.route("/uploader",methods=['GET','POST'])
def uploader():
    if 'user' in session and session['user']==params['admin_user']:
        if request.method=='POST':
            f=request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
            flash('Uploaded Successfully!')
            return redirect('/dashboard')
    return redirect("/dashboard")

@app.route("/contact",methods = ['GET','POST'])
def Contact():
    if(request.method=='POST'):
        Name=request.form.get('Name')       ##in paranthesis Name and others are from Contact.html
        email=request.form.get('Email') ##---eqn 2
        phone=request.form.get('Phone')
        message=request.form.get('Message')

        entry=Contacts(name=Name,email=email.lower(),phone_num=phone,msg=message,date=datetime.now())  #LHS from Eqn 1 and RHS from Eqn 2
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from ' + Name,  
                        sender=email.lower(),
                        recipients = [params["gmail-user"]],
                        body = message + "\n" + "Phone-Number: "+phone,
                        )
    return render_template('contact.html',params=params)
app.run(debug=True)
