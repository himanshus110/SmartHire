import nltk
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from InstructorEmbedding import INSTRUCTOR
from sentence_transformers import CrossEncoder

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')


instruction_JD = "Represent the Job Description Details for Retrieving supporting Resumes:"
instruction_Resume = "Represent the Resume Documents for Retrieval:"
crossencoder_name = 'cross-encoder/stsb-roberta-large'
instructor_name = 'hkunlp/instructor-large'

crossencoder = CrossEncoder(crossencoder_name)
model = INSTRUCTOR(instructor_name)
#crossencoder_name = 'cross-encoder/stsb-roberta-large'
#instructor_name = 'hkunlp/instructor-large'


class ResumeSearch:
    def __init__(self):
        #self.crossencoder = CrossEncoder(crossencoder_name)
        #self.model = INSTRUCTOR(instructor_name)
        pass

    def get_wordnet_pos(self, word):
        tag = nltk.pos_tag([word])[0][1][0].upper()
        tag_dict = {"J": wordnet.ADJ,
                    "N": wordnet.NOUN,
                    "V": wordnet.VERB,
                    "R": wordnet.ADV}
        return tag_dict.get(tag, wordnet.NOUN)

    def preprocess_text(self, text):
        # Tokenize the text into words
        words = word_tokenize(text)

        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        filtered_words = [word for word in words if word.lower() not in stop_words]

        # Lemmatize the words
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, self.get_wordnet_pos(word)) for word in filtered_words]

        # Combine the words back into a single string
        processed_text = ' '.join(lemmatized_words)

        return processed_text

    def get_top_10(self, job_desc, resume_list):
        # Preprocess the Job description and Resumes
        processed_job_desc = self.preprocess_text(job_desc)
        #processed_resumes = []
        for resume in resume_list:
          resume["text"] = self.preprocess_text(resume["text"])

        #processed_resumes = [self.preprocess_text(resume) for resume in resume_list]
        print(1)
        # Embed the Job description and Resume List
        embeddings_JD = model.encode([[instruction_JD,processed_job_desc]])
        print(2)
        corpus = []
        for res in resume_list:
          corpus.append([instruction_Resume,res["text"]])
          #corpus = [[instruction_Resume,res] for res in processed_resumes]
        embeddings_Resume = model.encode(corpus)
        print(3)

        # Calculate the cosine similarities
        similarities = cosine_similarity(embeddings_JD,embeddings_Resume)
        print(4)

        # Convert the list to np array
        my_array = np.array(similarities[0])
        # Retrieve the top 10 resumes from the list of resumes
        top_10_indices = np.argsort(my_array)[::-1][:10]

        shortlisted_resumes = [resume_list[i] for i in top_10_indices]

        return shortlisted_resumes

    def rerank_resumes(self, job_desc, resume_shortlist):
        # Use cross encoders for reranking
        scores = [crossencoder.predict([(job_desc, res["text"])]) for res in resume_shortlist]
        scores = [scores[i][0] for i in range(len(scores))]
        # Get the top 5 scores
        top_5 = np.argsort(scores)[::-1][:5]
        # Get the top 5 resumes
        top_resumes = [resume_shortlist[ind] for ind in top_5]
        resume_id = [res['id'] for res in top_resumes]
        return resume_id



