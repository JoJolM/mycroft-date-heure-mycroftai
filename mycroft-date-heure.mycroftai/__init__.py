# import des différents modules nécessaires
import datetime
import re
import pytz
import time
import tzlocal
from astral import Astral
import holidays

from adapt.intent import IntentBuilder
import mycroft.audio
from mycroft.util.format import pronounce_number, nice_date, nice_time
from mycroft.util.lang.format_de import nice_time_de, pronounce_ordinal_de
from mycroft.messagebus.message import Message
from mycroft import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.parse import extract_datetime, fuzzy_match, extract_number, normalize
from mycroft.util.time import now_utc, default_timezone, to_local
from mycroft.skills.core import resting_screen_handler

class HorlogeSkill(MycroftSkill):

    def __init__(self):
        #print("__init__")
        print("1")
        super(HorlogeSkill, self).__init__("HorlogeSkill")
        self.astral = Astral()
        self.display_time = None
        self.display_tz = None
        self.answering_query = False 

    def initialize(self):
        # commence un callback qui aura lieu toute les 10s
        # TODO: ajoute un mechanisme qui fait en sorte de que le timer
        #       qui ne commence que lorsque les paramètres UI sont vérifiés 
        #       cependant ça requiert un notifieur pour les paramètres 
        #       se met à jour depuis le web
        #print("initialize")
        print("2")
        now = datetime.datetime.now()
        callback_time = (datetime.datetime(now.year, now.month, now.day, now.hour, now.minute) 
                + datetime.timedelta(seconds=60))
        self.schedule_repeating_event(self.update_display, callback_time, 10)
    @property 
    def platform(self):
        """ Prends la chaine de charactère identifiant la platforme  
        Return:
            str: identiant de platforrm ie. "mycroft_mark_1",
            "mycroft_mark_2" et None si non standard 
        """
        # dans notre cas cette fonction va retourner "mycroft_mark_1"
        print("platform")
        #print("3")
        if self.config_core and self.config_core.get("enclosure"):
            print(self.config_core["enclosure"].get("platform"))
            return self.config_core["enclosure"].get("platform")
        else:
            print("Return None")
            return None
    @property
    def use_24hour(self):
        print("use_24hour")
        #print("4")
        return self.config_core.get('time_format') == 'full'

    def get_timezone(self, locale):
        print("get_timezone")
        #print("5")
        try:
            #gère les noms de villes connues ex: "New York", "Paris", ect...
            return pytz.timezone(self.astral[locale].timezone)
        except:
            print("try_1 failed")
            pass
        try:
            # gère du code tel que "Nice/France"
            return pytz.timezone(locale)
        except:
            print("try_2 failed")
            pass
        timezones = self.translate_namedvalues("timezone.value")
        for timezone in timezones:
            if locale.lower() == timezone.lower():
                # suppose que la traduction est correcte
                return pytz.timezone(timezone[timezone].strip())
        target = locale.lower()
        best = None 
        for name in pytz.all_timezones:
            normalized = name.lower().replace("_"," ").split("/")
            if len(normalized)== 1:
                pct = fuzzy_match(normalized[0], target)
            elif len(normalized) >=2:
                pct= fuzzy_match(normalized[1], target)
                pct2 = fuzzy_match(normalized[-2]+ " "+ normalized[-1], target)
                pct3 = fuzzy_match(normalized[-1]+ " "+ normalized[-2], target)
                pct = max(pct, pct2, pct3)
            if not best or pct >= best[0]:
                best = (pct ,name)
        if best and best[0] > 0.8 :
            return pytz.timezone(best[1])
        if best and best[0] > 0.3:
            say = re.sub(r"([a-z])([A-Z])",r"\g<1> \g<2>", best[1])
            say = say.replace("_"," ")
            say = say.split("/")
            say.reverse
            say = " ".join(say)
            if self.ask_yesno("vouliez.vous.dire",  data={"zone_name": say}) == "yes":
                return pytz.timezone(best[1])

        return None
    def get_local_datetime(self, location, dtUTC=None):
        print("get_local_datetime")
        #print("6")
        if not dtUTC:
            #print("6.1")
            print("dtUTC not set") 
            dtUTC = now_utc()
        if self.display_tz:
            #print("6.2")
            print("display timezone available")
            # montre les dates demandées par l'utilisateur dans certaines timeezone
            tz = self.display_tz
        else:
            #print("6.3")
            print("display timezone not available")
            tz = self.get_timezone(self.location_timezone)

        if location :
            print("location available")
            tz = self.get_timezone(location)
        if not tz: 
            self.speak_dialog("timezone.pas.trouve", {"location": location})
            return None 
        #print("6.4")
        print("return from get_local_datetime")
        return dtUTC.astimezone(tz)

    def get_display_date(self, day = None, location=None):
        print("get_display_date")
        #print("7")
        if not day:
            print("get local time(location)")
            day = self.get_local_datetime(location)
        if self.config_core.get('date_format') == 'MDY':
            return day.strftime("%-m/%-d/%Y")
        else:
            print("return date_format")
            return day.strftime("%Y/%-d/%-m")
    def get_display_current_time(self, location=None, dtUTC=None):
        print("get_display_current_time")
        #print("8")
        dt = self.get_local_datetime(location, dtUTC)
        print(dt)
        if not dt:
            return None 

        return nice_time(dt, self.lang, speech=False,
                        use_24hour=self.use_24hour)
    def get_spoken_current_time(self, location=None, dtUTC=None, force_ampm=False):
        print("get_spoken_current_time")
        #print("9")
        dt = self.get_local_datetime(location, dtUTC)
        if not dt:
            print("9.1")
            return
        say_am_pm= bool(location) or force_ampm

        s= nice_time(dt, self.lang, speech = True, 
                use_24hour=self.use_24hour, use_ampm=say_am_pm)
        print("exit from get_spoken_current_time")
        return s

    def display(self, display_time):
        print("display")
        #print("10")
        if display_time:
            if self.platform == "mycroft_mark_1":
                self.display_gui(dislplay_time)
            self.display_gui(display_time)
            
    def display_gui(self, display_time):
        print("display_gui")
        #print("11")
        """Affiche le temps sur le mycroft gui."""
        self.gui.clear()
        self.gui['time_string'] = display_time
        self.gui['ampm_string'] = '' 
        self.gui['date_string'] = self.get_display_date()
        self.gui.show_page('time.qml')
    def _is_display_idle(self):
        print("is_display_idle")
        #print("12")

        return self.enclosure.display_manager.get_active() == ''

    def update_display(self, force= False):
        print("update_display")
        #print("13")

        if self.answering_query:
            #print('13.1')
            print("answering_query available")
            return
        print("answering_query not available")
        self.gui['time_string'] = self.get_display_current_time()
        self.gui['date_string'] = self.get_display_date()
        self.gui['ampm_string'] = '' # TODO

        if self.settings.get("show_time", False):

            if (force is True) or self._is__display_idle():
                current_time = self.get_display_current_time()
                if self.displayed_time != current_time:
                    self.displayed_time = current_time
                    self.display(current_time)
                    self.enclosure.display_manager.remove_active()

            else :
                self.displayed_time = None
        else :
            if self.display_time:
                if self._is_display_idle():
                    self.enclosure.display_manager.remove_active()
                self.displayed_time = None




    @intent_file_handler("Quelle.heure.il.est.intent")

    def handle_query_time_alt(self, message):
        print("handle_query_time_alt")
        #print("14")
        self.handle_query_time(message)

    def _extract_location(self, utt):
        print("_extract_location")
        #print("15")

        rx_file= self.find_resource('location.rx', 'regex')

        if rx_file:
            with open(rx_file) as f:
                for pat in f.read().splitlines():
                    pat = pat.strip()
                    if pat and pat[0] == "#":
                        continue
                    res = re.search(pat, utt)
                    if res:
                        try:
                            return res.group("Location")
                        except IndexError:
                            pass
        return None

    ######################################################################
    ## Requêtes temps / display

    @intent_handler(IntentBuilder("").require("requete").require("Temps").optionally("Location"))
    
    def handle_query_time(self, message):
        print("handle_query_time")
        #print("16")
        utt = message.data.get('utterance',"")
        print("utt="+ utt)
        location = self._extract_location(utt)
        current_time = self.get_spoken_current_time(location)
        if not current_time:
            return
        #l'énonce
        self.speak_dialog("", {"time": current_time})

        # affiche l'heure 
        self.answering_query = True
        self.display(self.get_display_current_time(location))
        time.sleep(5)
        mycroft.audio.wait_while_speaking()
        self.answering_query = False
        self.displayed_time = None

    @intent_file_handler("Quelle.heure.sera.t.il.intent")
    def handle_query_future_time(self, message):
        #print("handle_query_future_time")
        print("17")
        utt = normalize(message.data.get('utterance',"").lower())
        extract = extract_datetime(utt)
        if extract:
            dt = extract[0]
            utt = extract[1]
        location = self._extract_location(utt)
        future_time = self.get_spoken_current_time(location, dt, True)
        if not future_time:
            return

        #l'énonce
        self.speak_dialog("temps.futur")

def create_skill():
    return HorlogeSkill()
