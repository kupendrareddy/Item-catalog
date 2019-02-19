#! /usr/bin/env python3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from database_setup import *

engine = create_engine('sqlite:///companywithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create sample users
User1 = User(name="kupendra Reddy", email="kupendrareddy321@gmail.com",
             picture='https://lh5.googleusercontent.com/-xRRw-nXh5gY/'
             'AAAAAAAAAAI/AAAAAAAAEL4/3mUxtgmOv8o/photo.jpg')
session.add(User1)
session.commit()
print "Done to add  user1"
# Create sample companys
company1 = Company(user_id=1, name="Fastrack", description="good",
                   pic='https://yt3.ggpht.com/a-/AAuE7mBSC1OwL31jgdzsDm87'
                   'Lr0hyw3q3egyAV3bwA=s900-mo-c-c0xffffffff-rj-k-no')

session.add(company1)
session.commit()

company2 = Company(user_id=1, name="rolex", description="good",
                   pic='https://www.rolex.com/content/dam/rolexcom/retailers/'
                   'plaques/retailer/official-retailer-plaque-en.jpg')

session.add(company2)
session.commit()
company3 = Company(user_id=1, name="timewell", description="good",
                   pic='https://image3.mouthshut.com/'
                   'images/imagesp/925036643s.jpg')

session.add(company3)
session.commit()

watchItem1 = Watches(user_id=1, name="watch", description="good",
                     price="$2.99",
                     pic1='https://n2.sdlcdn.com/imgs/h/3/a/Speed-Time-Fast'
                     'rack-Watch-3039SM05-SDL064415124-1-e8641.jpg',
                     company_id=1)
session.add(watchItem1)
session.commit()

watchItem2 = Watches(user_id=1, name="watch1", description="good",
                     price="$2.99",
                     pic1='https://n2.sdlcdn.com/imgs/h/3/a/Speed-Time-Fast'
                     'rack-Watch-3039SM05-SDL064415124-1-e8641.jpg',
                     company_id=2)
session.add(watchItem2)
session.commit()


watchItem3 = Watches(user_id=1, name="watch1", description="good",
                     price="$2.99",
                     pic1='https://n2.sdlcdn.com/imgs/h/3/a/Speed-Time-Fas'
                     'track-Watch-3039SM05-SDL064415124-1-e8641.jpg',
                     company_id=3)

session.add(watchItem3)
session.commit()


print("Your database has been inserted!\n")
