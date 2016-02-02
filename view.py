import datetime, random, json, re, os
from functools import wraps
from flask import render_template, jsonify, request, g, session
from flask import current_app as app
from flask.ext.login import current_user, login_required, login_user
from flask_classy import FlaskView, route
import re
from werkzeug.exceptions import HTTPException

from charter.core.extInstance import csrf
from charter.core.models import Text, Word, Hieroglyph, Radical, Action, Notification, User, Activity
from charter.core.models import News, text_word, ApiLog, UserAchievement, Achievement, db

from charter.core.settings.base import SQLALCHEMY_DATABASE_URI
from sqlalchemy.sql import text, func
from sqlalchemy import create_engine

from charter.modules.activity import send_drill_action, get_recent_activities
from charter.modules.skillmeter import get_hanzi_skill_meter
from charter.modules.library import get_texts_list, get_book_text
from charter.modules.drill import get_drill_set, get_selection_data
from charter.modules.login import login_usr, register_usr, change_pwd
from charter.modules.quizz import get_word_quiz_variants, get_hanzi_quiz_variants

def api_log(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        api_log =ApiLog()
        api_log.api_name = request.endpoint
        try:
            api_log.params = json.dumps(request.json)
        except HTTPException as e:
            print(e)

        api_log.user_id = g.user.id

        db.session.add(api_log)
        db.session.commit()

        ret = f(*args, **kwargs)

        return ret
    return wrapped

class ApiView(FlaskView):
    @route('Login', endpoint='Login', methods=['POST'])
    def loginUser(self): return login_usr(self)

    @route('Register', endpoint='Register', methods=['POST'])
    def registerUser(self): return register_usr(self)

    @login_required
    @route('/ChangePassword', endpoint='ChangePassword', methods=['POST'])
    def change_password(self): return change_pwd(self)

    @login_required
    @route('/', endpoint='api', methods=['POST'])
    def main(self): return 'No data'

    @login_required
    @route('/GetWordQuizVariants', endpoint='GetWordQuizVariants', methods=['POST'])
    def GetWordQuizVariants(self):  return get_word_quiz_variants(self)

    @login_required
    @route('/GetHanziQuizVariants', endpoint='GetHanziQuizVariants', methods=['POST'])
    def GetHanziQuizVariants(self): return get_hanzi_quiz_variants(self)

    @login_required
    @api_log
    @route('/GetDrillSet', endpoint='GetDrillSet', methods=['POST'])
    def GetDrillSet(self): return get_drill_set(request)

    @login_required
    @route('/GetDrillSelection', endpoint='GetDrillSelection', methods=['POST'])
    def GetDrillSelection(self): return get_selection_data(self)

    @login_required
    @route('/GetTextsList', endpoint='GetTextsList', methods=['GET', 'POST'])
    @api_log
    def GetTextsList(self): return get_texts_list(self)
    
    @login_required
    @route('/GetBookText', endpoint='GetBookText', methods=['POST'])
    @api_log
    def get_book_text(self):  return get_book_text(self)

    @login_required
    @route('/GetHanziSkillMeter', endpoint='GetHanziSkillMeter', methods=['POST'])
    def GetHanziSkillMeter(self):   return get_hanzi_skill_meter(self)
    
    @login_required
    @route('/SendDrillAction', endpoint='SendDrillAction', methods=['POST'])
    def SendDrillAction(self):   return send_drill_action(self)
    
    @login_required
    @route('/GetRecentActivities', endpoint='GetRecentActivities', methods=['POST'])
    def GetRecentActivities(self):   return get_recent_activities(self)


    # done
    @login_required
    @route('/GetNewNotifications', endpoint='GetNewNotifications', methods=['POST'])
    def get_new_notifications(self):
        """
        :param

        :return:
        {
            'notifications':[
                {'id':35,
                 'timestamp': 1382293453,
                 'text':'Staff you should know, bro',
                 'event':'blog/omg.html'
                 'new': true
                }
            ]
        }
        """

        # user = User.query.get(2)
        user = g.user
        user_note = [note for note in user.notification if note.new]

        notifications = self.make_notification_collection(user_note)

        return jsonify({'notifications': notifications})

    # done
    @login_required
    @route('/GetAllNotifications', endpoint='GetAllNotifications', methods=['POST'])
    def get_all_notifications(self):
        """
        :param
        {
            "offset":0,
            "limit":5
        }
        :return:
        {
            'notifications':[
                {
                    'id':35,
                    'timestamp': 1382293453,
                    'text':'Staff you should know, bro',
                    'event':'blog/omg.html'
                    'new': true/false
                }
            ]
        }
        """

        limit = request.json['limit']
        offset = request.json['offset']

        # user = User.query.get(2)
        user = g.user
        user_note = Notification.query.filter(Notification.user_id == user.id)\
                                      .order_by(Notification.created.desc())\
                                      .offset(offset)\
                                      .limit(limit)\
                                      .all()

        notifications = self.make_notification_collection(user_note)

        return jsonify({'notifications': notifications})

    def make_notification_collection(self, user_notifications):
        notifications = []
        for note in user_notifications:
            elem = {
                'id': note.id,
                'timestamp': note.created,
                'text': note.text,
                'event': note.event,
                'new': note.new
            }
            notifications.append(elem)

            # TODO maybe it makes sense to verify if frontend catch this response
            if note.new:
                note.new = False
                db.session.add(note)

        db.session.commit()

        return notifications

    # done
    @login_required
    @route('/GetNews', endpoint='GetNews', methods=['POST'])
    def get_news(self):
        """
        :param
        {
            "offset":0,
            "limit":5
        }
        :return:
        {
            'news':[
                {
                    'id':35,
                    'timestamp': 1382293453,
                    'text':'Staff you should know, bro',
                    'title':'Some title',
                    'link':'blog/omg.html'
                }
            ]
        }

        """

        limit = request.json['limit']
        offset = request.json['offset']
        news = News.query.order_by(News.created.desc()).offset(offset).limit(limit).all()
        news_collection = self.make_news_collection(news)

        return jsonify({'news': news_collection})
    def make_news_collection(self, news):
        news_collection = []
        for item in news:
            elem = {'id': item.id,
                    'timestamp': item.created,
                    'text': item.text,
                    'title': item.title,
                    'link': item.link
                    }
            news_collection.append(elem)

        return news_collection

    @login_required
    @route('/GetHanziTree', endpoint='GetHanziTree', methods=['POST'])
    @api_log
    def get_hanzi_tree(self):
        hanzi_id = request.json['hanzi_id']
        hieroglyph = Hieroglyph.query.get(hanzi_id)
        return jsonify(json.loads(hieroglyph.tree_cache))


    # done
    @login_required
    @route('/GetSmtToLearn', endpoint='GetSmtToLearn', methods=['POST'])
    def get_smt_to_learn(self):
        """
        GetSmtToLearn():
            when:
                User clicks on corresponding button

        :param
            {"timelimit":5|15|30|0}
        :return:
        {'learning' :{
            'activity':drill|tree|text
            'api-method':'GetWordFreqDrillSet'
            'param':{'start':12, 'end': 114'}
        }}
        """

        timelimit = request.json['timelimit']

        if timelimit:
            learning = {
                'activity': 'drill',
                'api-method': 'GetWordHskDrillSet',
                'param': {'level': [1, 3, 5], 'start': 12, 'end': 114}
            }

        return jsonify({'learning': learning})

    # done
    @login_required
    @route('/GetNewAchievements', endpoint='GetNewAchievements', methods=['POST'])
    def get_new_achievements(self):
        """

        :return:
        {
            'achivements':[
                {'id':23,
                'timestamp':1382293453,
                'title':'Family member',
                'text':'For faithfully using our service for more than 12 hours',
                'instruction':'Do some actions on memiora with time lag not more than 5 mins',
                'new': True}
            ]
        }
        """

        # user = User.query.get(2)
        user = g.user
        self.check_achievement(user)
        user_achievement = UserAchievement.query.filter(UserAchievement.new, UserAchievement.user_id == user.id)\
                                                .order_by(UserAchievement.created.desc())\
                                                .all()

        collection = self.make_achievement_collection(user_achievement)

        return jsonify({'achievements': collection})

    # done
    @login_required
    @route('/GetAchievements', endpoint='GetAchievements', methods=['GET', 'POST'])
    def get_achievements(self):
        """

        :param
        {
            'offset':0,
            'limit':5
        }
        :return:
        {
            'achivements':[
                {'id':23,
                'timestamp':1382293453,
                'title':'Family member',
                'text':'For faithfully using our service for more than 12 hours',
                'instruction':'Do some actions on memiora with time lag not more than 5 mins',
                'new': True}
            ]
        }
        """

        offset = request.json['offset']
        limit = request.json['limit']

        # user = User.query.get(20)
        user = g.user
        self.check_achievement(user)
        user_achievement = UserAchievement.query.filter(UserAchievement.user_id == user.id)\
                                                .order_by(UserAchievement.created.desc())\
                                                .offset(offset)\
                                                .limit(limit)\
                                                .all()

        collection = self.make_achievement_collection(user_achievement)

        return jsonify({'achievements': collection})

    def make_achievement_collection(self, user_achievement):
        collection = []
        for item in user_achievement:
            elem = {
                'id': item.achievement_id,
                'timestamp': item.created,
                'title': item.achievement.title,
                'text': item.achievement.text,
                'instruction': item.achievement.instruction,
                'new': item.new
            }

            collection.append(elem)
            # TODO maybe it makes sense to verify if frontend catch this response
            if item.new:
                item.new = False
                db.session.add(item)

        db.session.commit()

        return collection

    def check_achievement(self, user):
        achievements = Achievement.query.all()

        for achievement in achievements:
            if achievement not in user.achievements:
                param = json.loads(achievement.params)

                # TODO Action.action value most be identical with api Action.action
                if param[0] == 'DrillNext + DrillPrev':
                    count_prev = Action.query.filter(Action.user_id == user.id,
                                                     Action.action == 'DrillPrev') \
                        .count()
                    count_next = Action.query.filter(Action.user_id == user.id,
                                                     Action.action == 'DrillNext') \
                        .count()
                    count_total = count_prev + count_next
                    if count_total > param[1]:
                        self.set_new_achievement(achievement, user)

                if param[0] == 'DrillExclude':
                    count_exclude = Action.query.filter(Action.user_id == user.id,
                                                        Action.action == 'DrillExclude').count()
                    if count_exclude > param[1]:
                        self.set_new_achievement(achievement, user)

                if param[0] == 'DrillExtremeTick':
                    count_extreme = Action.query.filter(Action.user_id == user.id,
                                                        Action.action == 'DrillExtremeTick') \
                        .count()
                    if count_extreme > param[1]:
                        self.set_new_achievement(achievement, user)

                if param[0] == 'TreeSelect':
                    count_tree_select = Action.query.filter(Action.user_id == user.id,
                                                            Action.action == 'TreeSelect') \
                        .count()
                    if count_tree_select > param[1]:
                        self.set_new_achievement(achievement, user)

                if param[0] == 'QuizCorrect':
                    count_quiz_correct = Action.query.filter(Action.user_id == user.id,
                                                             Action.action == 'QuizCorrect') \
                        .count()
                    if count_quiz_correct > param[1]:
                        self.set_new_achievement(achievement, user)

                if param[0] == 'QuizIncorrect':
                    count_quiz_incorrect = Action.query.filter(Action.user_id == user.id,
                                                               Action.action == 'QuizIncorrect') \
                        .count()
                    if count_quiz_incorrect > param[1]:
                        self.set_new_achievement(achievement, user)

    def set_new_achievement(self, achievement, user):
        add_achievement = UserAchievement()
        add_achievement.user_id = user.id
        add_achievement.achievement_id = achievement.id
        add_achievement.user = user
        add_achievement.achievement = achievement
        db.session.add(add_achievement)
        db.session.commit()

    @login_required
    @route('/GetLearningCurve', endpoint='GetLearningCurve', methods=['GET', 'POST'])
    def get_learning_curve(self):
        # Get data from user action log, how many entries for each user in some period
        #     when:
        #         When login to display on homepage
        #     params:
        #         {'points':15}
        #     return:
        #         ### Number of data entries == points in params
        #         ### Value is sum() of hanzi & words which 'last_seen' is > than corresponding date
        #         {
        #             data:[
        #                 ['19/09':87],
        #                 ['18/09':23],
        #                 ['17/09':11],
        #                 ['16/09':222],
        #                 ['15/09':156],
        #                 ['14/09':123],
        #                 ['13/09':1]
        #             ]
        #
        #         }

        # user = User.query.get(2)
        user = g.user
        # offset = request.json['offset']
        offset = 90
        delta = datetime.timedelta(offset)
        finish = datetime.date.today() + datetime.timedelta(1)
        start = finish - delta

        actions = Action.query.with_entities(Action.created)\
                              .filter(Action.created.between(start, finish), Action.user_id == user.id).all()

        data = sum(actions, ())
        action_list = []
        for action in data:
            action_list.append(action.strftime('%Y/%m/%d'))

        collection = {}
        for day in self.daterange(start, finish):
            day = day.strftime('%Y/%m/%d')
            collection[day] = action_list.count(day)
        return jsonify({'set': collection})
    def daterange(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + datetime.timedelta(n)
    
    @login_required
    @route('/GetUserWordKnowledge', endpoint='GetUserWordKnowledge', methods=['POST'])
    def get_user_word_knowledge(self):
        """

        GetUserWordKnowledge():
            why:
                to define is familiar + text sorting
            when:
                During login

        :return:
            Must return all words that are active + complexPassive + complexActive
            ['id':483, 'passive':20, 'active':65]
            {'words':{
                172:[37,45],
                483:[20,65]
                }
            }
        """

        words = {
            '172': [37, 45],
            '483': [20, 65],
            '487': [211, 165],
            '485': [222, 265],
            '484': [233, 365],
            '477': [444, 465],
            '466': [555, 565],
            '455': [667, 665],
            '444': [777, 765],
            '411': [888, 865],
        }

        return jsonify({'words': words})

    @login_required
    @route('/GetKnowledge', endpoint='GetKnowledge', methods=['GET', 'POST'])
    def get_knowledge(self):
        """
        Backend_comments:
            Give info about all active words
            All data is taken from Word obj
        Frontend_comments:
            Call when user login
            Must be stored in local storage and partitiinally updated after each action, using response
            Must be totally updated every $KnowledgeUpdatePeriod seconds

        :return:
        {
            knowledge:[
                {'id':32, 'passive':45, 'active':67}
                {'id':38, 'passive':45, 'active':67}
                {'id':31, 'passive':0, 'active':0}
            ]
        }
        """

        # user = User.query.get(2)
        user = g.user
        test = user.word_assocs

        knowledge = []
        for word in user.word_assocs:
            elem ={
                'id': word.word_id,
                'passive': word.complexPassive(),
                'active': word.complexActive()
            }
            knowledge.append(elem)

        return jsonify({'knowledge': knowledge})

    @csrf.exempt
    @route('/WordsPictures', endpoint='WordsPictures', methods=['GET', 'POST'])
    def word_pictures(self):
        count = Word.query.filter(Word.iv > 0).count()
        offset = request.json['offset']
        limit = request.json['limit']

        words = Word.query.filter(Word.iv > 0)\
                          .order_by(Word.id)\
                          .offset(offset)\
                          .limit(limit)\
                          .all()

        collection = []
        for word in words:
            image, pictures = self.image_set(word)
            elem = {
                'id': word.id,
                'raw': word.raw,
                'translation': word.translation.split(';')[:3],
                'image': word.image,
                # 'pictures': pictures
            }
            collection.append(elem)

        return jsonify({'picture': collection, 'count': count})

    def image_set(self, word):
        search_name = '{}_'.format(word.id)
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if re.match(search_name, f)]
        main_picture = word.image
        main = ''
        for file in files:
            if str(main_picture) in file:
                main = file
                files.remove(file)

        return main, sorted(files)

    # @csrf.exempt
    # @route('/ChangeImage', endpoint='ChangeImage', methods=['GET', 'POST'])
    # def change_image(self):
    #     image = request.json['picture_name']
    #
    #     word_id = image.split('_')[0]
    #     word = Word.query.get(word_id)
    #     word.image = image.split('.')[0]
    #     db.session.add(word)
    #     db.session.commit()
    #
    #     return jsonify({'result': 'changed'})

        word_id = image.split('_')[0]
        word = Word.query.get(word_id)
        word.image = image.split('.')[0]
        db.session.add(word)
        db.session.commit()

        return jsonify({'result': 'changed'})