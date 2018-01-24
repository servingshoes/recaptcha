#!/usr/bin/env python

from logging import getLogger
from subprocess import check_output
from requests import Session
from lxml import etree
from time import sleep, monotonic
from pdb import set_trace
from tempfile import mkstemp
from os import fdopen

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC

lg=getLogger(__name__)

class recaptcha():
    rdict_fn='/home/pooh/work/recaptcha/dict'
    
    def __init__(self, max_retries=5):
        '''Wants self.driver in the subclass'''
        
        self.s = Session()
        self.s.headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0'
        }
        etree.set_default_parser(etree.HTMLParser())

        self.max_retries=max_retries
        self.searchprov='google' # bing

    def click_item(self, el: 'WebElement or xpath string'):
        """Click a given WebElement or element by xpath (if argument is a string)
        """
        if isinstance(el, str):
            el = self.driver.find_element_by_xpath(el)

        # I don't know why, but there are lots of problems with actionchains
        el.click()
        return

    def load(self):
        lg.debug('Recaptcha load')
        WebDriverWait(self.driver, 30).until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.CSS_SELECTOR, 'iframe[src*="https://www.google.com/recaptcha")]'))
        )

        el=WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div.recaptcha-checkbox-checkmark'))
        )
        lg.debug('Got visible')

        el.click()
        lg.debug('Clicked solve box')
        
        # action = ActionChains(self.driver)
        # action.move_to_element_with_offset(el, 5, 6)
        # #action.move_to_element(item)
        # action.click().perform()

        return el

    def solve_concept_captcha(self):
        """Tries to solve concept captcha by searching google for term * concept and
        seeing how many results are there. The most mentioned win.

        """
        lg.debug('in solve_concept_captcha')

        #set_trace()
        tree = etree.fromstring(self.driver.page_source)

        a = tree.xpath('//div[@class="rc-text-payload"]')[0]
        concept = a.xpath('//div[@class="rc-text-instructions"]//span/text()')[0]
        lg.debug('concept: {}'.format(concept))

        coords = {}
        for rownum, row in enumerate(a.xpath('//table[@class="rc-text-choices"]//tr')):
            for colnum, col in enumerate(row.xpath('td')):
                coords[col.text] = (rownum+1, colnum+1)
        lg.debug(coords)

        index_base = '//table[@class="rc-text-choices"]//tr[{}]/td[{}]'

        # Now we ask search engine about “"item" "concept"” for all items
        res = []
        for i in coords:
            if self.searchprov == 'bing':
                r = self.s.get('https://www.bing.com/search',
                               params={'q': '"{}" near:5 "{}"'.format(i, concept)}
                              )
                #http://www.bing.com/search?q=learning+near%3A5+%22common+site%22+&qs=n&form=QBRE&pq=learning+near%3A5+%22common+site%22+&sc=0-30&sp=-1&sk=&cvid=D21D0354F30C4B3E890536D2065B8390

                tree = etree.fromstring(r.text)
                #open('out/'+i,'w').write(r.text)
                cnt = tree.xpath('//span[@class="sb_count"]/text()')
                lg.debug('{}: {}'.format(i, cnt))

                if cnt:
                    res.append((i, int(cnt[0].split()[0].replace(',', '')))) # English
                    #res.append((i, int(cnt[0].replace('\xa0', '').split()[-1]))) # Russian
            elif self.searchprov == 'google':
                r = self.s.get('https://www.google.ru/search',
                               params={'q': '"{}" "{}"'.format(i, concept)}
                              )
                tree = etree.fromstring(r.text)
                #open('out/'+i,'w').write(r.text)
                cnt = tree.xpath('//div[@id="resultStats"]/text()')

                lg.debug('{}: {}'.format(i, cnt))
                # if "No results" in
                if cnt:
                    nr = tree.xpath('//div[@id="res"]//text()')[0]
                    lg.debug('-{}-'.format(nr))
                    if nr == 'Нет результатов для ': cnt = []

                if cnt:
                    res.append((i, int(cnt[0].replace('\xa0', '').split()[-1])))

        res.sort(key=lambda x: x[1], reverse=True)

        # Now res contains items sorted by hits on google, we'll click them
        # one by one and see what captcha will say. I suspect they are always
        # three, so let's click them at once.
        lg.debug(res)

        # Can do nothing about it, too few results to pick from, retry
        if len(res) < 2:
            self.click_item('id("recaptcha-reload-button")')
            return False

        #sleep(10000)
        num=2 if len(coords) == 5 else 3
        for i in range(min(num, len(res))):
            #self.action.move_to_element(self.driver.find_element_by_xpath(index_base.format(*coords[res[i][0]]))).click().perform()
            self.click_item(index_base.format(*coords[res[i][0]]))
            #sleep(randint(0, 20)/10)

        self.click_item('id("recaptcha-verify-button")')

        css=(
            'div.rc-text-select-more div.rc-text-select-fewer '
            'div.rc-text-verify-failed div.rc-audiochallenge-error-message'
        )
        try:
            element = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css))
            )
        except TimeoutException: # Aha, we've apparently solved that
            # self.driver.switch_to.default_content()
            #el=self.driver.find_element_by_id('recaptcha-anchor')
            # el=self.driver.find_element_by_xpath('//span[@id="recaptcha-anchor"]')
            # print(el.get_attribute('class'))
            #print(self.driver.page_source)
            return True

        # Some error, let's check what is its class?
        lg.debug(element.get_attribute('class'))

        return False

    def solve_audio_captcha(self):
        """Programmatically solves the audio captcha. See the doc for more information,
        but in short it uses pocketshpinx with dictionary consisting only of numbers.
        """
        digits = { 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                   'five': '5', 'six': '6', 'seven': '7', 'eight': '8',
                   'nine': '9', 'zero': '0' }

        href = self.driver.find_element_by_class_name("rc-audiochallenge-tdownload-link").get_attribute('href')

        fd, fn=mkstemp('.ogg')
        fd=fdopen(fd, 'wb') # Make normal object out of description
        
        fnwav=fn.replace('.ogg','.wav')
        
        r=self.s.get(href, params={'id': 'ogg'})
        if r.status_code != 200: # Some big problem
            raise PermissionError
        fd.write(r.content)
        # for chunk in r.iter_content(1024):
        #     fd.write(chunk)
        fd.close()

        stime=monotonic() # When we got the file, we'll sleep needed number of secs
        res=check_output(["soxi "+fn+" | awk '/^Duration/{print $3}'"],
                         shell=True)
        if not res:
            lg.error('Wrong file returned by recaptcha. Are we blocked? Consult {}'.format(fn))
            return False
        
        # It's safer to sleep extra second
        tosleep=int(res.decode().split(':')[-1].split('.')[0])+1

        res=check_output(["ffmpeg -y -i {0} -ar 16000 {1} 2>&-; pocketsphinx_continuous -infile {1} -dict {2} 2>&- | awk -F': ' '{{printf $2\" \"}}'".format(fn, fnwav, self.rdict_fn)], shell=True)
        #remove(fn); remove(fnwav)
        #result="".join(digits[x] for x in res.decode().split())
        result="".join(map(digits.get, res.decode().split()))
        lg.debug(result)

        res_field=self.driver.find_element_by_id('audio-response')
        res_field.send_keys(result)

        tosleep-=monotonic()-stime
        lg.debug('sleeping before sending captcha result: {}'.format(tosleep))
        if tosleep>0: sleep(tosleep)

        self.click_item('id("recaptcha-verify-button")')

        #set_trace()
        css='div.rc-text-select-more div.rc-text-select-fewer '\
             'div.rc-text-verify-failed div.rc-imageselect-incorrect-response '\
             'div.rc-audiochallenge-error-message'
        try:
            el=WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css))
            )
        except TimeoutException: # Aha, we've apparently solved that
            lg.info('Captcha solved?')
            open('err.html','w').write(self.driver.page_source)
            return True
        except WebDriverException as e:
            # selenium.common.exceptions.WebDriverException: Message: TypeError: can't access dead object
            # For hidden captcha
            lg.info(e.args)
            
            return True

        # Some error, let's check what is its class?
        lg.debug(el.get_attribute('class'))

        return False

    td_ec=EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        'div.rc-text-challenge, div.rc-audiochallenge-tdownload'))
    # If play widget is already presented, this will be invisible, but still there
    ab_ec=EC.visibility_of_element_located((
        By.CSS_SELECTOR, '#recaptcha-audio-button'))

    def solve_challenge(self) -> bool:
        """Solves a single ReCaptcha challenge panel.
        Support both audio captcha and text concept captcha
        """
        success = False

        lg.debug('Clicking on audio button')
        # Play audio widget may already be present (by default)
        el = WebDriverWait(self.driver, 20).until(
            lambda driver: self.ab_ec(driver) or self.td_ec(driver)
        )
        #set_trace()

        if isinstance(el, EC.element_to_be_clickable): # Need to click the button then
            el.click()

        #open('1.html','w').write(self.driver.page_source)

        # Audio is blocked because IP looks like issuing automated requests
        if 'Automated' in self.driver.page_source:            
            lg.warning('Automated')
            
        # There are two types of captcha, normal audio, where we need
        # to download a file and solve it with pocketsphynx, and concepts
        for _ in range(self.max_retries):
            element = WebDriverWait(self.driver, 10).until(self.td_ec)
            cl = element.get_attribute('class')
            lg.debug('Challenge class: '+cl)

            success = self.solve_audio_captcha() if \
                      cl == 'rc-audiochallenge-tdownload' else \
                      self.solve_concept_captcha()
            lg.info('solve_challenge: {}'.format(success))
            if success: break # We've solved it
        else:
            lg.warning('Failed to solve captcha')

        return success

    def solve_nocaptcha(self):
        '''Solve the captcha with nocaptcha'''
        self.load()

        def check_style(driver, el):
            '''Now need to see what happened there. Check an attribute to see if we're successful.'''
            attr=el.get_attribute('aria-checked')
            lg.debug('check_style: '+attr)
            return attr == 'true'

        lg.debug('Before check_style')
        timeout=False
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: check_style(
                    driver, self.driver.find_element_by_id('recaptcha-anchor'))
            )
        except TimeoutException:
            timeout=True # Next (very soon) we'll see what happened 

        res=self.driver.find_element_by_id('recaptcha-anchor').get_attribute('aria-checked')        
        lg.debug('Final: '+res)
        
        self.driver.switch_to.default_content() # We're back on main page
        
        return res == 'true'

    def solve(self, noload=False) -> bool:
        """Solves a ReCaptcha on the page. No xpath is necessary because:
        1: There is only ever one ReCaptcha on an active page
        2: ReCaptchas are an iframe, so they always have the same internal xpaths
        """

        if not noload:
            try:
                lg.debug('Calling recaptcha load')
                el=self.load()
            except TimeoutException:
                lg.warning('Recaptcha not available')
                # driver.switch_to.default_content()
                # clickItem(driver.find_element_by_xpath('//li[@id="supplier"]/a'))
                #self.driver.refresh()
                return False

            #open('1.html','w').write(self.driver.page_source)
            self.driver.switch_to.default_content()
            #open('2.html','w').write(self.driver.page_source)

        lg.debug('Switching to challenge')
        WebDriverWait(self.driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((
                By.CSS_SELECTOR, '[title="recaptcha challenge"]'))
        )
        lg.debug('Switched to challenge')

        try:
            solved=self.solve_challenge()
        except:
            raise
        finally:
            #Return focus to the main page
            self.driver.switch_to.default_content()

        return solved
