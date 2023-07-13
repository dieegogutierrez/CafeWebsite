from datetime import datetime
from flask import render_template, url_for, request, flash, redirect, abort
from website import app, db, bcrypt, mail
from website.models import User, Cafe
from website.forms import RegistrationForm, LoginForm, UpdateAccountForm, CafeForm, RequestResetForm, ResetPasswordForm
from flask_login import current_user, login_user, login_required, logout_user
from flask_mail import Message


@app.context_processor
def inject_year():
    current_year = datetime.now().year
    return dict(year=current_year)


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route('/cafe')
def cafe():
    page = request.args.get('page', 1, type=int)
    cafes = Cafe.query.order_by(Cafe.id.desc()).paginate(page=page, per_page=8)
    return render_template('cafe.html', title='Cafes', cafes=cafes)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Your are already logged in.', 'info')
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Welcome, {current_user.username}! You can now edit or add cafes.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('cafe'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    flash(f'Goodbye, {current_user.username}! You have successfully logged out!', 'success')
    logout_user()
    return redirect(url_for('home'))


@app.route('/account/<int:user_id>', methods=['GET', 'POST'])
@login_required
def account(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    cafes = Cafe.query.filter_by(author=user).order_by(Cafe.id.desc()).paginate(page=page, per_page=4)
    if user.id != current_user.id:
        return render_template('account.html', title='Account', user=user, cafes=cafes)
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account', user_id=current_user.id))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form, user=current_user, cafes=cafes)


@app.route('/cafe/new', methods=['GET', 'POST'])
@login_required
def new_cafe():
    form = CafeForm()
    if form.validate_on_submit():
        post = Cafe(name=form.name.data, map_url=form.map_url.data, img_url=form.img_url.data, location=form.location.data, has_sockets=form.has_sockets.data, has_toilet=form.has_toilet.data, has_wifi=form.has_wifi.data, can_take_calls=form.can_take_calls.data, seats=form.seats.data, coffee_price=form.coffee_price.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your cafe has been created!', 'success')
        return redirect(url_for('cafe'))
    return render_template('new_cafe.html', title='New Cafe', legend='New Cafe', form=form)


@app.route("/cafe/<int:post_id>")
def cafe_post(post_id):
    post = Cafe.query.get_or_404(post_id)
    return render_template('cafe_post.html', title=post.name, cafe=post)


@app.route("/cafe/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_cafe(post_id):
    post = Cafe.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = CafeForm()
    if form.validate_on_submit():
        post.name = form.name.data
        post.map_url = form.map_url.data
        post.img_url = form.img_url.data
        post.location = form.location.data
        post.has_sockets = form.has_sockets.data
        post.has_toilet = form.has_toilet.data
        post.has_wifi = form.has_wifi.data
        post.can_take_calls = form.can_take_calls.data
        post.seats = form.seats.data
        post.coffee_price = form.coffee_price.data
        db.session.commit()
        flash('Your cafe has been updated!', 'success')
        return redirect(url_for('cafe_post', post_id=post.id))
    elif request.method == 'GET':
        form.name.data = post.name
        form.map_url.data = post.map_url
        form.img_url.data = post.img_url
        form.location.data = post.location
        form.has_sockets.data = post.has_sockets
        form.has_toilet.data = post.has_toilet
        form.has_wifi.data = post.has_wifi
        form.can_take_calls.data = post.can_take_calls
        form.seats.data = post.seats
        form.coffee_price.data = post.coffee_price
    return render_template('new_cafe.html', title='Update Post', form=form, legend='Update Post')


@app.route("/cafe/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_cafe(post_id):
    post = Cafe.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your cafe has been deleted!', 'success')
    return redirect(url_for('cafe'))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        flash('Your are already logged in.', 'info')
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        flash('Your are already logged in.', 'info')
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.errorhandler(403)
def error_403(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def error_500(error):
    return render_template('500.html'), 500