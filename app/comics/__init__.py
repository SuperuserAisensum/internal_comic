from flask import Blueprint

bp = Blueprint('comics', __name__)

from app.comics import routes 