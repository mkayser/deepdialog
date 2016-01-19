from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, RadioField, SelectField
from wtforms.validators import Required, AnyOf


class LoginForm(Form):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[Required()])
    submit = SubmitField('Play!')


class RestaurantForm(Form):
    """Select a restaurant from a list of radio buttons"""
    restaurants = RadioField('Restaurants', choices=[], coerce=int, validators=[AnyOf(range(0,10))])
    submit = SubmitField('Agree on a restaurant!')
