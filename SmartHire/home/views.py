from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
import uuid
from .models import Job, Resume, QuestionBank, CandidateResponse
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
# Create your views here.
import io
import json
from django.urls import reverse
from .lang_chain_model import *
from .utils import *
from .scripts import *
from .sort_resume import ResumeSearch

subscription_key = "" #Enter your key here
endpoint = "" # Enter your endpoint here

computervision_client = ComputerVisionClient(
        endpoint, CognitiveServicesCredentials(subscription_key))



def home(request):
    return render(request, 'home.html')


def upload_files(request):
    if request.method == 'POST':
        files = request.FILES.getlist('resume')
        description = request.POST.get('description')
        
        job_instance = Job()
        job_instance.description = description
        job_instance.save()

        # Save the uploaded files to the model instance
        item_list=[]
        ranking=[]
        for file in files:
            resume_item = Resume(job=job_instance, file=file)
            resume_item.save()
            # ranking.append(resume_item.id)
            item = pdf_to_text(resume_item)
            item_list.append(item)
            # print(item)

        print("Shortlisting Candidates")
        res_search = ResumeSearch()
        top_10 = res_search.get_top_10(description, item_list)

        print("Rranking for top 5 Candidates")
        ranking = res_search.rerank_resumes(description, top_10)

        print("Saving Questions for Candidates")
        for num in ranking:
            resume = Resume.objects.get(id=num)
            resume.shortlisted=True
            resume.save()
            item = pdf_to_text(resume)
            name,phone,email,work = extract_info(resume= item)
            resume.mobile_no = phone
            resume.summary = work
            resume.name = name
            resume.email = email
            resume.shortlisted=True
            resume.save()
            final_questions = get_question(job_desc=description, resume = item)
            count = 1
            for ques in final_questions:
                ques_item = QuestionBank(resume = resume, question = ques)
                ques_item.save()
                count+=1
                if count == 4:
                    break
        redirect_url = reverse('send-email', kwargs={'jobid': job_instance.id})
        return redirect(redirect_url)

    return render(request, 'index.html')


def cv_ranking(request, pk):
    serial_no = 1
    resume_list = Resume.objects.filter(job=pk,shortlisted=True)
    candidate_details=[]
    for resume in resume_list:
        candidate={}
        candidate['jobid']=pk
        candidate['id']=resume.id
        candidate['name']=resume.name
        candidate['mobile_no']=resume.mobile_no
        candidate['email']=resume.email
        candidate['work']=resume.summary
        candidate['serial_no']=serial_no
        candidate_details.append(candidate)
        serial_no+=1
    return render(request, 'cv_ranking.html',context={'candidate_details': candidate_details})


def send_email(request, jobid):
    print("Sending Mails")
    resume_list=Resume.objects.filter(job=jobid, shortlisted = True)
    for resume in resume_list:
        recipient = resume.email
        print(recipient)
        interview_url = "http://localhost:8000/interview/"+str(resume.id)+"/"
        send_email_to_client(message=str("Please attend this interview "+str(interview_url)), recipient="c.harshit2102@gmail.com")
    print("All Mails Sent")
    redirect_url = reverse('cv_ranking', kwargs={'pk': jobid})
    return redirect(redirect_url)

def interview(request, pk):
    questions = QuestionBank.objects.filter(resume=pk)
    ques_list=[]
    for ques in questions:
        item={}
        item['id']=ques.id
        item['question']=ques.question
        ques_list.append(item)
    print("Starting Interview")
    screening(ques_list)
    print("Interview Ended")

    print("Evaluating answers")
    with open('home/transcript.txt','r') as f:
        for line in f:
            line_list=line.split('#')
            if line_list[0] is not None:
                ques = QuestionBank.objects.get(id=line_list[0])
                response = CandidateResponse(question=ques,answer=line_list[1])
                feedback=interview_response(ques.question,line_list[1])
                response.feedback=feedback
                response.save()
    print("Saved Responses and Feedback")
    return render(request, 'interview.html')

def feedback(request, pk):
    ques_list = QuestionBank.objects.filter(resume=pk)
    candidate = Resume.objects.get(id=pk)

    feedback_list=[]
    count = 1
    for ques in ques_list:
        candidateresp = CandidateResponse.objects.filter(question=ques)
        for ans in candidateresp:
            feedback_item={}
            feedback_item['serial_no']=count
            feedback_item['question']=ques.question
            feedback_item['answer']=ans.answer
            feedback_item['feedback']=ans.feedback
            feedback_list.append(feedback_item)
            break
        count+=1
        if count == 4:
            break
    return render(request, 'feedback.html',context={'feedback': feedback_list, 'candidate': candidate})


def pdf_to_text(resume):
        file_path = resume.file.path
        with open(file_path, "rb") as reader:
                    file = reader.read()
        reader = io.BytesIO(file)
        read_response = computervision_client.read_in_stream(reader, raw=True)
        read_operation_location = read_response.headers["Operation-Location"]
        # Grab the ID from the URL
        operation_id = read_operation_location.split("/")[-1]

        # Call the "GET" API and wait for it to retrieve the results
        while True:
            read_result = computervision_client.get_read_result(operation_id)
            if read_result.status not in ["notStarted", "running"]:
                break

        textract_response=azure_to_aws(read_result)
        text_list = []
        for block in textract_response['Blocks']:
            if block['BlockType']=='WORD':
                    text_list.append(block['Text'])
        text = ' '.join(text_list)

        item = dict()
        item['id']=resume.id
        item['text']=text

        return item

def azure_to_aws(read_result):
    image_width = read_result.as_dict()["analyze_result"]["read_results"][0]["width"]
    image_height = read_result.as_dict()["analyze_result"]["read_results"][0]["height"]
    azure_response = read_result.as_dict()["analyze_result"]["read_results"][0]["lines"]
    textract_response = {
        "DocumentMetadata": {"Pages": 1},
        "Blocks": [],
        "AnalyzeDocumentModelVersion": "",
        "ResponseMetadata": {},
    }

    
    for line in azure_response:
        TextType = line["appearance"]["style"]["name"]
        if TextType == "handwritting":
            TextType = 'HANDWRITTING'
        else:
            TextType = 'PRINTED'
        for word in line["words"]:
            b_box = word["bounding_box"]
            x_coords = b_box[::2]
            y_coords = b_box[1::2]
            left = min(x_coords)
            top = min(y_coords)
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            geometry = {
                "BoundingBox": {
                    "Width": width / image_width,
                    "Height": height / image_height,
                    "Left": left / image_width,
                    "Top": top / image_height,
                },
                "Polygon": [
                    {"X": x_coords[0] / image_width, "Y": y_coords[0] / image_height},
                    {"X": x_coords[1] / image_width, "Y": y_coords[1] / image_height},
                    {"X": x_coords[2] / image_width, "Y": y_coords[2] / image_height},
                    {"X": x_coords[3] / image_width, "Y": y_coords[3] / image_height},
                ],
            }
            block = {
                "BlockType": "WORD",
                "Geometry": geometry,
                "Text": word["text"],
                "Id": str(uuid.uuid4()),
                "Confidence": word["confidence"],
                "TextType": str(TextType),
            }
            textract_response["Blocks"].append(block)
    return textract_response