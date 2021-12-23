from datetime import datetime
import uuid


# User class
class User():
    def __init__(self,name,email,reg_date):
        # Main initialiser
        self.name = name
        self.email = email
        self.reg_date = reg_date

    @classmethod
    def make_from_dict(cls, d):
        # Initialise User object from a dictionary
        return cls(d['name'], d['email'],d['reg_date'])

    def dict(self):
        # Return dictionary representation of the object
        return {
            "name": self.name,
            "email": self.email,
            "reg_date": self.reg_date
        }

    def display_name(self):
        return self.name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    # def get_id(self):
    #     return self.id


# Anonymous user class
class Anonymous():

    @property
    def is_authenticated(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return True

    # def get_id(self):
    #     return None
