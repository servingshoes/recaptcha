#!/usr/bin/python

import subprocess
import time
from lxml import etree
import requests
from codecs import decode
from json import loads
import re
import base64
from logging import getLogger

lg=getLogger(__name__)

class captcha_old():
    def get_captcha(self):
        while False: # True:
            r=super().do('get',
                      'https://www.visa.com/supplierlocator/rest/captcha' )
            res=self.handle_reply(r)
            if not res: continue

            d=res['data'][0]
            proc = subprocess.Popen('base64 -d | convert -black-threshold 90% - -| tesseract -psm 8 - - -c tessedit_char_whitelist="0123456789+"',
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, shell=True )
            outs, errs = proc.communicate(input=bytes(d['base64Data'], 'utf-8'))
            try:
                val=eval(outs.strip())
            except SyntaxError:
                continue
            break

        return d['captchaId'], val

class captcha:        
    digits={ 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
             'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'zero': '0' }
    v='r20171011122914' # Version, it's the same everywhere

    headers={
        'Accept': '*/*', #'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language':'en-US,en;q=0.5',
        #'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0'
    }
    headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/56.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Upgrade-Insecure-Requests': '1',
    }
    fallback_url='https://www.google.com/recaptcha/api/fallback'
    payload_url='https://www.google.com/recaptcha/api2/payload'

    def __init__(self, k, ref):
        etree.set_default_parser(etree.HTMLParser())
        self.s=requests.Session()
        # CZ: 213.211.36.146:8080
        #self.s.proxies={'https': '187.141.117.215:8080'}
        self.s.headers=self.headers.copy()
        # 'https://www.google.com/recaptcha/api2/demo'
        self.s.headers['Referer']=ref
        self.s.params={'k': k}
        self.k=k

    def get_anchor(self, size):
        if 0:
            class a: pass
            r=a()
            r.text=open('rc0.html').read()
            tree=etree.fromstring(r.text)
        else:
            r=self.s.get('https://www.google.com/recaptcha/api2/anchor',
                         params={'k': self.k, 'co': self.co, 'hl': 'en',
                                 'v': self.v, 'size': size })
            tree=etree.fromstring(r.text)
            open('rc0.html', 'w').write(r.text)
        
        self.c=tree.xpath('//input[@id="recaptcha-token"]/@value')[0]
        lg.debug('c: '+self.c)

        for line in r.text.splitlines():
            ls=line.strip()
            if ls.startswith('recaptcha.anchor.Main.init'):
                res=ls.split('"')[1]
                break
        j=loads(decode(res, 'unicode-escape'))
        #j=loads(re.sub(r',+',',',decode(res, 'unicode-escape')))
        for i in j:
            #print(i)
            if type(i) is list:
                if i[0] == 'bgdata':
                    self.bg=i[3]
                    break #continue

        r=self.s.get('https://www.google.com/recaptcha/api2/bframe',
                     params={'hl': 'en', 'k': self.k, 'v': self.v })
        # Get token for the next operation, it's in rresp
        open('rc1.html', 'w').write(r.text)

    def get_visa_captcha(self, size='normal'):
        begin=time.clock_gettime(time.CLOCK_REALTIME)

        self.get_anchor(size)
        
        # r=self.s.get('https://www.google.com/recaptcha/api2/payload',
        #              params={'c': c, 'k': self.k })
        data={
            'reason': 'fi',
            'c': '03AJzQf7P9QKF_kt4-J0TnYea95FySLgCrTOGeSACnfHJcIWHvbQhm0IPu7baGhp7vOrslm_aObgwE8kP1Hvv4n7eZcrpYKjIfYvwFQe_4UNKphu3KoMVfAaeCSqoNabgUpvcl7_U9Mb4F048tyN9TBjCLUtKQ2Ry5LhCORaAr0WfMSHzI-fQJ-XiAhV8nqBokwXj7p7Yha7Hc4ESO8KCSUiqCd4V5jFkp7tE02XmdoNkxVeU3WqlUedeRHYPcLbhl97fEFJs0UwwWdxoKlPNsd9KhQj6tu0SiNJWugCYVdEAreOHRuaa5qgK6fVGqEcq6wZN9daElbxwG4rvrtB8mJWtgLlmhAYsxsCekL4yIt8taqrUa4_jBWCnyx5AjICJZ4ohRAxLtvZ2o5fi2JvuBGiRoxZ9dPQ02-GcxlrxDwnhoog31w6yDp7A',
            'bg': '!ioygjK1HGHvRJ_2FVF5B6bPjkwY6teAHAAAB2FcAAALFnATRkJFDF-faaFxye740Njvf3GD2jOYl3b40CySwp74nygzZI2YUMiOXJmk_vxw_QKdvmVgmMHl0djvGODvitZPOJQnVkCkP3vTcX1HiccHFyvzfDoQ0meT2L2-2sejH7umQDoTvJj84L66Qt3KqUW2WOOK-Jh7HHX0DYNAtN2dU1KnuXr2b3GtnwqLo8oL6ReAuxeXwsja1v-35lIKOg7vaqrfhFFEoiafXEZBUN2f_Pu25ioYCFO3smh2Cs2zeeKDCk3FnGECpFti30V586xTrwcjxUmyP5k1Cdo9izMgkEjQroRfsZYEzouyZtU84eERKLZ7tWAc9oKf-PbmKqw2_0lmzkiw6IQ3RmFhdv-jtd6ZkArA5Ou7Cx2JpNRXECMedYQaOd0rBXvDdyn0FHiveZFtH7bc5plfJF-zGyOJPvbn4mE-qa-Pw3dr1hQ_Vtupvo1Psnq7Q2OOxU4ddJFYbD-O-M2XB-179S5nBg4NPlHNR-sKTHfk5wR1J2MaD6IxKwhvG4KxcQ9TiWFkjYB2xLqrWHRyGTXxOiU4xt8QroQGEpF_0YQX_rDGvBq_-1v0lH_yMskazK7jvGu8se8uNizeZkDZ7wSi0HFVJ3sn8XP895qRpIppmiQfrRz1PYB4JzdvjjufiQvB26LnL5Q8f0bkoro-vbveZR2JLHZrXAnJc30Gs7wb3tjvu_J145rP_GT-pviK322IuyodSClru0QF0odvqW-m7HSJvZ-jA0NkFeatJ2BDT61MfSewFcjMGrGwpcKSfmy-rc_wp6nGeCw7dLqoYYY3HKDljy7VCWnT592ykHeESwLPi-AY4jLEYzaECeuoDBR5dyrmsGNwc3U3ecWSWicFsoyyLuqPHxdrmz6xliKDKykUtxOpXiY9IID-SuFF-gnk83u9j6TqT-8rhtXAiD1AZ1vzHSU-K2E5LRKfh_nyeoOBrTPBsuWONbJxdunxMwNDU3x3RyPDw3fZ88Bh04-eCBUCiq3O_JowPystR8Ufkfr1hSUL8_SeKmZobG0fReQsq628O1mmtlPFzM-i5uO1lJVpHFBGcdBUPOaJu4SZS-gHqsTxejcp6A2XGY4pG7hlbLhAkMwYCmYezthd9q96x1HW5IH6IkT0DMtQzWEAYmGOrqLFLKo_KzkcCyTu73Rcs1QDJDgqiChaMs22bt1QDlSl_iZB2LOlC-1CkbpXXQmO4egYki0mz3dsM2qW_HkSzE1CFtfg03SE62_AX12xukTELm-EdFeJTUrDzNyYnAH-8Bho3gqWr1sbbbYYeYxn39y5eeDltSNTchpBx_bRaBo8Q4O6IrVFKULSNcIZu7FAwp1WeyPbjLG5aIebBOG8d1bHnEu9iL5WufhEz5vG_ePhnwYFNAOkyFuOWmBrxfkcMJeoJ9fsQrGhRTbvdSm1hWvrSvaWOM2pkqEs1AlBluI3ZNpXOmIMMrReQNm7aj0C1MZX2Q2IEGWYuCyUE2wSFpUHzjDgfbFPQrhEujktrrmxoTrlsq3ip5h0sHXaM-81bICTQxpr3fsaqFASZiPwp37qz22oF2GVvL-UA3_QmQoO3CWCKItKIjFd_Vf6T98JjFR6xP_7klosZsyNhA3LfCoqwxmXQfIfnaaKUQVK69PJ2UuYsxQyz',
            'c': self.c,
            'bg': self.bg
        }
        data1={
                          'v': self.v,
                          'reason': 'fi',
                          # bcr=[1191357687,-1336698219,1840704017,-1328066315,-1177223129,1082087059,-1230085435]
                          #'c': c,
                          # chr=[11,54,66]
                          # hr=-2094963032
                          #'bg': bg
                      }
        r=self.s.post('https://www.google.com/recaptcha/api2/reload',
                      params={'k': self.k },
                      headers={
                          'Referer': 'https://www.google.com/recaptcha/api2/bframe?hl=en&v={}&k={}'.format(self.v, self.k)
                      },
                      data=data)
        j=loads(r.text[5:])
        for i in j:
            if isinstance(i, list): continue
            print(i)
        return # Stop here

        r=self.s.post('https://www.google.com/recaptcha/api2/reload',
                     params={'k': self.k }, data={'v': v, 'c': c, 'reason': 'a'})
        for line in r.text.splitlines():
            ls=line.strip()
            if ls.startswith('["rresp"'):
                c=ls.split(',')[1].strip('"')
                break

        t1=time.clock_gettime(time.CLOCK_REALTIME)
        r=self.s.get('https://www.google.com/recaptcha/api2/payload',
                     params={'c': c, 'k': self.k, 'id': 'ogg' })
        with open('audio.ogg', 'wb') as fd:
            for chunk in r.iter_content(1024):
                fd.write(chunk)

        stime=time.monotonic() # When we got the file, we'll sleep needed number of secs
        res=subprocess.check_output(["soxi audio.ogg | awk '/^Duration/{print $3}'"], shell=True)
        tosleep=int(res.decode().split(':')[-1].split('.')[0])+1 # Safer to sleep extra
        res=subprocess.check_output(["ffmpeg -y -i audio.ogg -ar 16000 audio.wav 2>&-; pocketsphinx_continuous -infile audio.wav -dict dict 2>&- | awk -F': ' '{printf $2\" \"}'"], shell=True)
        result="".join(map(lambda x: self.digits[x], res.decode().split()))
        print(result)
        resp=bytes('{{"response":"{}"}}'.format(result),'ascii')
        tosleep-=time.monotonic()-stime
        print('sleeping before sending captcha result', tosleep)
        time.sleep(tosleep)
        t2=time.clock_gettime(time.CLOCK_REALTIME)
        data={'c': c, 'v': v, 'ct':int((t1-begin)*1000),
              't': int((t2-begin)*1000),
              'response': base64.b64encode(resp).replace(b'=',b'.').decode('ascii')}
        print(data)
        r=self.s.post('https://www.google.com/recaptcha/api2/userverify',
                      params={'k': self.k}, data=data )
        print(r.text)
        for line in r.text.splitlines():
            ls=line.strip()
            if ls.startswith('["uvresp"'):
                ret=ls.split(',')[2]
                print(ret)
                break

    # http://www.google.com/recaptcha/demo/
    def get_captcha_v1(self):
        def get_challenge(txt):
            tree=etree.fromstring(r.text, self.parser)
            for line in r.text.splitlines():
                ls=line.strip()
                if ls.startswith('challenge :'):
                    return ls.split("'")[1]

        r=self.s.get('http://www.google.com/recaptcha/api/challenge', params={'k': self.k} )
        c=get_challenge(r.text)
        #with open('1.html', 'w') as f: f.write(r.text)

        r=self.s.get('http://www.google.com/recaptcha/api/reload',
                     params={'c': c, 'k': self.k, 'reason': 'a', 'type': 'audio',
                             'lang': 'en', 'new_audio_default': "1"})
        #with open('1.html', 'w') as f: f.write(r.text)
        token=r.text.split("'")[1]

        r=self.s.get('http://www.google.com/recaptcha/api/audio.mp3',
                     params={ 'c': token, 'k': None } )
        with open('audio.mp3', 'wb') as f:
            for chunk in r.iter_content(1024): f.write(chunk)
        
        stime=time.monotonic() # When we got the file, we'll sleep needed number of secs
        # res=subprocess.check_output(["soxi audio.ogg | awk '/^Duration/{print $3}'"], shell=True)
        res=subprocess.check_output(["exiftool audio.mp3 | awk '/^Duration/{print $3}'"], shell=True)
        tosleep=int(res.decode().split(':')[-1].split('.')[0])+1 # Safer to sleep extra
        res=subprocess.check_output(["ffmpeg -y -i audio.mp3 -ar 16000 audio.wav 2>&-; pocketsphinx_continuous -infile audio.wav -dict dict 2>&- | awk -F': ' '{printf $2\" \"}'"], shell=True)
        result="".join(map(lambda x: self.digits[x], res.decode().split()))
        data={'recaptcha_challenge_field': token,
              'recaptcha_response_field': result, 'Button1': 'Submit'}
        print(data)
        tosleep-=time.monotonic()-stime
        print('sleeping before sending captcha result', tosleep)
        time.sleep(tosleep)
        r=self.s.post('http://www.google.com/recaptcha/demo/', data=data )
        print(r.text)

    # https://www.google.com/recaptcha/api2/demo
    def get_captcha_v2_nojs(self):
        r=self.s.get(self.fallback_url, params={'k': self.k} )
        tree=etree.fromstring(r.text, self.parser)
        c=tree.xpath('//form[@method="POST"]/input[@name="c"]/@value')[0]
        #logging.info(c)
        
        # headers['Referer']=ref
        # headers['Accept']='image/png,image/*;q=0.8,*/*;q=0.5'
        # r=s.get('https://www.google.com/recaptcha/api2/payload',
        #         params={ 'c': c, 'k': k }, headers=headers, stream=True)

        #captcha.headers['Accept']='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        r=self.s.post(self.fallback_url, data={'c': c, 'reason': 'a'})
        #with open('1.html', 'w') as f: f.write(r.text)

        tree=etree.fromstring(r.text, self.parser)
        c1=tree.xpath('//input[@name="c"]/@value')[0]
        #logging.info(c1)

        #captcha.headers['Accept']='audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5'
        if False:
            r=self.s.get(self.payload_url, stream=True,
                         params={ 'c': c1, 'id': 'ogg' } )
            with open('audio.ogg', 'wb') as f: f.write(r.raw.read())
        else:
            r=self.s.get(self.payload_url, stream=True,
                         params={ 'c': c1, 'type': 'audio' } )
            with open('audio.mp3', 'wb') as f: f.write(r.raw.read())
        stime=time.monotonic() # When we got the file, we'll sleep needed number of secs
        # res=subprocess.check_output(["soxi audio.ogg | awk '/^Duration/{print $3}'"], shell=True)
        res=subprocess.check_output(["exiftool audio.mp3 | awk '/^Duration/{print $3}'"], shell=True)
        tosleep=int(res.decode().split(':')[-1].split('.')[0])+1 # Safer to sleep extra
        res=subprocess.check_output(["ffmpeg -y -i audio.mp3 -ar 16000 audio.wav 2>&-; pocketsphinx_continuous -infile audio.wav -dict dict 2>&- | awk -F': ' '{printf $2\" \"}'"], shell=True)
        result="".join(map(lambda x: self.digits[x], res.decode().split()))
        if result == '330209137983232301233539442087878789217485323485600':
            print(self.s.proxies)
            return None
        else:
            print(self.s.proxies)
            exit()
        data={'c': c1, 'response': result}
        logging.info(data)
        #captcha.headers['Accept']='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        tosleep-=time.monotonic()-stime
        print('sleeping before sending captcha result', tosleep)
        time.sleep(tosleep)
        data={'recaptcha_challenge_field': c1, 'recaptcha_response_field': result}
        r=self.s.post(self.fallback_url, data=data )
        print(r.text)
        tree=etree.fromstring(r.text, self.parser)
        try:
            return tree.xpath('//textarea[@dir="ltr"]/text()')[0]
        except:
            return None

    def get_lin_captcha(self):
        self.fallback_url='https://www.google.com/recaptcha/api/noscript'
        r=self.s.get(self.fallback_url,
                     params={'k': self.k, 'is_audio': 'true'} )
        
        
        tree=etree.fromstring(r.text, self.parser)
        dl=tree.xpath('//center/a/@href')[0]
        rcf=tree.xpath('//form[@method="POST"]/input[@name="recaptcha_challenge_field"]/@value')[0]

        #captcha.headers['Accept']='audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5'
        r=self.s.get('https://www.google.com/recaptcha/api/'+dl, stream=True)
        with open('audio.mp3', 'wb') as f: f.write(r.raw.read())

        stime=time.monotonic() # When we got the file, we'll sleep needed number of secs
        # res=subprocess.check_output(["soxi audio.ogg | awk '/^Duration/{print $3}'"], shell=True)
        res=subprocess.check_output(["exiftool audio.mp3 | awk '/^Duration/{print $3}'"], shell=True)
        tosleep=int(res.decode().split(':')[-1].split('.')[0])+1 # Safer to sleep extra
        res=subprocess.check_output(["ffmpeg -y -i audio.mp3 -ar 16000 audio.wav 2>&-; pocketsphinx_continuous -infile audio.wav -dict dict 2>&- | awk -F': ' '{printf $2\" \"}'"], shell=True)
        result="".join(map(lambda x: self.digits[x], res.decode().split()))
        data={'recaptcha_challenge_field': rcf,
              'recaptcha_response_field': result, 'submit': "I'm a human"}
        logging.info(data)
        tosleep-=time.monotonic()-stime
        print('sleeping before sending captcha result', tosleep)
        time.sleep(tosleep)
        r=self.s.post(self.fallback_url, data=data)
        tree=etree.fromstring(r.text, self.parser)
        try:
            return tree.xpath('//textarea/text()')[0]
        except:
            return None

if __name__ == "__main__":
    ll=WARNING
    ll=INFO
    basicConfig(format='{asctime}: {message}', datefmt="%H:%M:%S",
                        style='{', level=ll)

    if 0: # Demo v1: https://www.google.com/recaptcha/demo
        c=captcha('6Ld4iQsAAAAAAM3nfX_K0vXaUudl2Gk0lpTF3REf',
                  'https://www.google.com/recaptcha/api2/demo')        
        print(c.get_captcha_v1())
    if 1: # Demo v2: https://www.google.com/recaptcha/api2/demo
        k='6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-'
        
        for i in open('captcha/good.txt'):
            c=captcha(k,
                      "https://www.google.com/recaptcha/api/fallback?k={}".format(k))
            c.s.proxies={'https': i.strip()}
            try:
                c.get_captcha_v2_nojs()
            except:
                pass

    if 0: # Visa
        c=captcha('6LcRzw8TAAAAAKehrqEDq3VNupCjazga0eeyLvbk',
                  'https://www.visa.com/supplierlocator/search/index.jsp')
        c.co='aHR0cHM6Ly93d3cudmlzYS5jb206NDQz'
        print(c.get_visa_captcha())
    if 0: # Linkedin
        c=captcha("6LcnacMSAAAAADoIuYvLUHSNLXdgUcq-jjqjBo5n",
                  'https://www.linkedin.com/uas/consumer-captcha')
        print(c.get_lin_captcha())

