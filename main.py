import os
import cv2
import math
import uuid
import praw
import urllib
import pytesseract
import numpy as np



# This script has 2 classes: Reddit and Image. Reddit is a class for the reddit API, PRAWN. This class handles
# interacting with reddit by fetching posts and images. The fetched images are thrown into an Image instance.
# This class handles saving the image, performing basic text-box detection, OCR, etc...

    
# Of course, I can't provide you with my personal API keys or username/password so I've censored those.
# Although I did save 5 examples in the project of input and output images that would result from
# running this script with valid PRAWN credentials.


class Reddit():
    
    def __init__(self, username, password, client_id, client_secret, user_agent = 'required'):
        
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.reddit = self._initialize()
        
    def _initialize(self):
        
        reddit = praw.Reddit(client_id = self.username,
                     client_secret = self.client_secret,
                     password = self.password,
                     username = self.username,
                     user_agent = self.user_agent)
        
        return reddit
    
    
    def scrape_sub_pictures(self, subreddit, sub_category = 'hot', n = 100):
        '''Scrapes a number of pictures from a reddit subreddit.'''
        
        subreddit = self.reddit.subreddit(subreddit)
        category = getattr(subreddit, sub_category)
        posts = list(category(limit = n))
        
        # post instances have dynamic attributes (see PRAW docs) so you have to tease out image attributes:
        posts = [post for post in posts if 'post_hint' in dir(post) if post.post_hint == 'image']
        image_urls = [post.preview['images'][0]['source']['url'] for post in posts]
        
        self.image_urls = image_urls
        
        
    def get_random_url(self):
        
        return np.random.choice(self.image_urls)
    
    
    def ocr_meme(self, url = self.get_random_url):
        '''Initializes an Image and performs basic text detection and OCR (WIP).'''
        
        image = Image(url)
        image.draw_contours()

        
        
class Image():
    
    def __init__(self, url):
        
        self.url = url
        self.uid = str(uuid.uuid4()) # Unique identifier
        self.path = os.path.join('images', self.uid)
        self.image = self.save_image_from_url()
        self.height, self.width, _ = self.image.shape
        self.contours = self.get_text_boxes()
        self.cropped_contours = self.crop_contours()
        self.contour_texts = self.get_contour_texts()
    
    
    def save_image_from_url(self):
        '''Saves the image from a URL to local and initializes a directory structure.'''
    
        # Create directory structure if it's not already in place
        if not os.path.exists('images'):
            os.makedirs('images')
                
        for directory in ['input_images', 'output_images', 'output_texts']:
            path = os.path.join('images', self.uid, directory)
            
            if not os.path.exists(path):
                os.makedirs(path)
                
        # Create a unique filename
        self.image_path = os.path.join(self.path, 'input_images', 'input.png')
        request = urllib.request.urlretrieve(self.url, self.image_path) 
        
        return cv2.imread(self.image_path)
        
        
    def get_text_boxes(self):
        '''A basic attempt to find text in image designed for advice animal formats.'''
        
        # Create a grayscale image and threshold it aggressively
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        thresh = 255 - thresh # invert the image
        self.thresh = thresh # save for later

        erosion_kernel = np.ones((1, 5)) # creating horizonatal kernal size for erosion
        dilation_kernel = np.ones((7,7)) # use a large dilation kernel to capture sparse words

        # Erode and then dilate
        erosion = cv2.erode(thresh, erosion_kernel, iterations = 1)
        dilated = cv2.dilate(erosion, dilation_kernel, iterations = 4) # dilate

        contours, hierarchy = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) # get contours

        # Narrow down contours to ones that likely contain text
        for contour in contours:
            [x,y,w,h] = cv2.boundingRect(contour)

            # remove contours that are too tall to be sections of text
            if h > w:
                contours.remove(contour)
                continue

            # remove contours that are too narrow to be sections of text
            if  w < self.width * .15:
                contours.remove(contour)
                continue

        return contours

    
    def crop_contours(self):
        '''Saves sections of self.thresh that contain previously found contours'''
        
        assert self.contours, 'You need to run self.get_text_boxes first or this image has no contours.'
        cropped_contours = []
        
        for contour in self.contours:
            [x,y,w,h] = cv2.boundingRect(contour)
            
            crop = self.thresh[y : y + h, x : x + w]
            cropped_contours.append(crop)
        
        return  cropped_contours
    
    
    def draw_contours(self, save = True):
        '''Draws contour boxes on an image and saves the output.'''
        
        copy = self.image.copy()
        
        for contour in self.contours:
            [x,y,w,h] = cv2.boundingRect(contour)
            
            cv2.rectangle(copy, (x,y),(x+w,y+h),(0,255,0),2)
        
        if save:
            output_path = os.path.join(self.path, 'output_images', 'contours.png')
            cv2.imwrite(output_path, copy)
    
    
    def get_contour_texts(self, config = '-l eng --oem 1 --psm 3', save = True):
        '''Performs basic OCR on contour boxes. I can not stress how much of a WIP this is.'''
        
        texts = []
        for image in self.cropped_contours:
            
            dilation_kernel = np.ones((2, 2)) # use a large dilation kernel to capture sparse words
            dilated = cv2.dilate(image, dilation_kernel, iterations = 1) # dilate
            
            # Attempt at OCR. still a WIP due to package issues...
            text = pytesseract.image_to_string(dilated, config = config) 
            texts.append(text)

        if save:
            path = os.path.join(self.path, 'output_texts', 'text.txt')
            
            with open(path, "w") as file:
                file.write('\n'.join(texts))
                
        return texts

    
    
if __name__ == "__main__":
    
    reddit = Reddit('###################', '###################', '###################', '###################')
    reddit.scrape_sub_pictures('adviceanimals', 'hot')
    reddit.ocr_meme()