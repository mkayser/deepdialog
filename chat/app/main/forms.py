from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, RadioField
from wtforms.validators import Required


class LoginForm(Form):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[Required()])
    submit = SubmitField('Play!')


class RestaurantForm(Form):
    """Select a restaurant from a list of radio buttons"""
    restaurant_labels = RadioField('Restaurants', choices=[], validators=[Required()])
    submit = SubmitField('Agree on a restaurant!')
