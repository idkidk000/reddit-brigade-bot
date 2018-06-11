import praw, time, random, threading, datetime

reddit_accounts = [
    ('USER1','PASS1'),
    ('USER2','PASS2')
]

reddit_user_agent='CommentStreamer/0.1'
reddit_client_id='REDDIT_CLIENT_ID'
reddit_client_secret='REDDIT_CLIENT_SECRET'

report_users = [
    'USER1',
    'USER2'
]

report_disabled_subs = [
    'SUB1',
    'SUB2'
]

downvote_phrases = [
    'PHRASE1',
    'PHRASE2'
]

downvote_users = [
    'USER1',
    'USER2'
]

downvote_subs = [
    'SUB1',
    'SUB2'
]

downvote_disabled_subs = [
    'SUB1',
    'SUB2'
]

upvote_users = [
    'USER1',
    'USER2'
]

upvote_subs = [
    'SUB1',
    'SUB2'
]

letter_chars           = [chr(x) for x in range(97,123)] #a-z
letter_chars          += [chr(x) for x in range(65,91)] #A-Z
punctuation_chars      = [x for x in '`¬!"£$%^&*()-=_+[]{};:\'@#~,./<>?\\| '] #standard uk punctuation
number_chars           = [str(x) for x in range(0,10)] #0-9
voting_threads         = []
upvote_users          += [reddit_account[0] for reddit_account in reddit_accounts]
enable_upvote          = True
enable_downvote        = True
enable_report          = True
thread_sleep_min_short = 60  #sleep times for short queue
thread_sleep_max_short = 240
thread_sleep_min_long  = 30  #sleep times for long queue
thread_sleep_max_long  = 120
thread_long_queue      = 80  #use _short timeouts when queue below this threadshold
thread_min_queue       = 20  #increase to make voting appear more random
thread_max_queue       = 100 #sleep loop is skipped if queue hits this size
vote_probability       = 0.6 #chance of passing a vote job to each thread. 1==always
log_file_name          = 'brigade_bot_'
body_parse_length      = 50
listen_for_commands    = False # log !commands for research

class VotingThread (threading.Thread):
    def __init__(self, reddit_username, reddit_password):
        threading.Thread.__init__(self)
        self.reddit = praw.Reddit(
            user_agent=reddit_user_agent,
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password)
        self.queue = []
        self.user = reddit_username
        log(self.user,'thread init')
    
    def enqueue(self, action, comment_id): #externally queue resolves to this method. internally self.queue is a list.
        self.queue.append((action,comment_id))
        
    def run(self):
        log(self.user,'thread start')
        #log(self.user,len(self.queue),'queue size',len(self.queue))
        while True:
            if len(self.queue) > thread_min_queue:
                #log(self.user,len(self.queue),'queue size',len(self.queue))
                data = self.queue.pop(random.randint(0,len(self.queue)-1)) #pull a random item from the queue
                #data = self.queue.pop(0) #TODO: comment this, uncomment line above. troubleshooting
                action = data[0]
                comment_id = data[1]                
                log(self.user,len(self.queue),'processing',action,comment_id)
                comment = praw.models.Comment(self.reddit,id=comment_id)
                if action == 'upvote':
                    try:
                        comment.upvote()
                    except:
                        pass
                elif action == 'downvote':
                    try:
                        comment.downvote()
                    except:
                        pass
                elif action == 'report':
                    try:
                        comment.downvote()
                        comment.report('Spam')
                    except:
                        pass
                
            if len(self.queue) < thread_max_queue:
                if len(self.queue)>=thread_long_queue:
                    sleep_secs = random.randint(thread_sleep_min_long, thread_sleep_max_long)
                else:
                    sleep_secs = random.randint(thread_sleep_min_short, thread_sleep_max_short)
                
                #only sleep 1s at a time and check the queue isn't full
                while sleep_secs > 0 and len(self.queue) < thread_max_queue:
                    time.sleep(1)
                    sleep_secs-=1
                        
    def user(self):
        return self.user
         
def main():
    reddit_anon = praw.Reddit(
        user_agent=reddit_user_agent,
        client_id=reddit_client_id,
        client_secret=reddit_client_secret)

    for reddit_account in reddit_accounts:
        voting_thread = VotingThread(reddit_account[0],reddit_account[1])
        voting_thread.start()
        voting_threads.append(voting_thread)

    subreddit = reddit_anon.subreddit('all')
    for comment in subreddit.stream.comments():
        process_comment(comment)

def queue_thread_action(action, comment):
    #log('queueing',action,str(comment.author).lower(), comment.permalink, normalize(comment.body[:50]))
    if action == 'upvote' and enable_upvote or action == 'downvote' and enable_downvote or action == 'report' and enable_report:   
        #log('queueing',action,comment.id,'https://www.reddit.com'+comment.permalink)
        queued_count = 0
        for voting_thread in voting_threads:
            if random.randint(0,100)/100.0<=vote_probability:
                #log('queued',voting_thread.user,action)
                voting_thread.enqueue(action, comment.id)
                queued_count += 1
        log('queued',queued_count,action+'s',comment.id,'https://www.reddit.com'+comment.permalink)

def process_comment(comment):
    sub = comment.subreddit_name_prefixed.lower()[2:]
    user = str(comment.author).lower()
    normalized_body = normalize(comment.body[:body_parse_length])
    
    if comment.body[0] == '!' and listen_for_commands:
        log('!command',normalize(comment.body[:body_parse_length], False, False, False),'https://www.reddit.com'+comment.permalink)


    if user in report_users and sub not in report_disabled_subs:
        if enable_report:
            queue_thread_action('report', comment)
        
    elif sub in upvote_subs or user in upvote_users:
        if enable_upvote:
            queue_thread_action('upvote', comment)
        
    elif ( sub in downvote_subs or user in downvote_users or normalized_body in downvote_phrases ) and sub not in downvote_disabled_subs:
        if enable_downvote:
            queue_thread_action('downvote', comment)
    
#    else:
#        log('no action',user,sub,normalized_body)
            
def normalize(in_string, lower_case=True, clear_numbers=True, clear_punctuation=True):
    out_string= ''
    if lower_case:
        in_string = in_string.lower()
    for c in in_string:
        if c in letter_chars or c in number_chars and not clear_numbers or c in punctuation_chars and not clear_punctuation:
            out_string += c
    return out_string

def log(a,b=None,c=None,d=None,e=None,f=None,g=None):
    log_text=str(datetime.datetime.time(datetime.datetime.now()))+' '+str(a)
    if b is not None: log_text+=' '+str(b)
    if c is not None: log_text+=' '+str(c)
    if d is not None: log_text+=' '+str(d)
    if e is not None: log_text+=' '+str(e)
    if f is not None: log_text+=' '+str(f)
    if g is not None: log_text+=' '+str(g)
    
    print(log_text)
    log_file = open(log_file_name+str(datetime.date.today())+'.log','a')
    log_file.write(log_text+'\n')
    log_file.close()

if __name__ == '__main__':
    main()
