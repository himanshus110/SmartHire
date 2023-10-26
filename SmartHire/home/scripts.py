import cv2
import time
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import speech_recognition as sr
import multiprocessing
# questions = [{'id':1,'question':
#         "What is your name?"},{'id':2,'question':
#         "Tell us about your experience?"}
#         # Add more questions here
#     ]

shared_list = list()

def add_question_overlay(frame, question):
    # Convert the frame to a Pillow image for text overlay
    
    img_pil = Image.fromarray(frame)

    # Set font properties
    font = ImageFont.truetype("arial.ttf", 20)
    text_color = (0, 0, 0)  # White color

    # Add the question as an overlay on the image
    draw = ImageDraw.Draw(img_pil)
    draw.text((10, 430), question, font=font, fill=text_color)

    # Convert back to OpenCV format (numpy array)
    frame_with_overlay = np.array(img_pil)

    return frame_with_overlay


def record_video(questions):
    # Open the video capture device (webcam)
    cap = cv2.VideoCapture(0)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
   
    size = (frame_width, frame_height)
    result = cv2.VideoWriter('interview.avi', 
                         cv2.VideoWriter_fourcc(*'MJPG'),
                         15, size)


    # Set the time limit for each question (in seconds)
    time_limit = 10

    for question in questions:

        start_time = time.time()

        while time.time() - start_time < time_limit:
            ret, frame = cap.read()
            result.write(frame)
        
            # Add the question overlay to the frame
            frame_with_overlay = add_question_overlay(frame, question['question'])

            # Display the frame with the question overlay
            cv2.imshow('Interview Question', frame_with_overlay)

            # Press 'q' to break out of the loop and move to the next question
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


    # Release video capture and close OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

def record_audio(questions):
    
    answers=[]
    recording_duration = 8 
    audio_list=[]
    for question in questions:

        recognizer = sr.Recognizer()

    # Set the recording duration in seconds # Adjust this as needed
        
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Recording...")
            audio = recognizer.listen(source,  phrase_time_limit=recording_duration)
            audio_list.append(audio)
    # recognize the speech
    try:
        for audio,question in zip(audio_list,questions):
            transcript = recognizer.recognize_google(audio)
            answers.append({'id':question['id'], 'answer': transcript})
            print("You said: " + transcript)
        # with open(f"{question['question']}.txt", 'w') as f:
        #     f.write(transcript)

        # save the audio
        # with open(f"{question['question']}.wav", "wb") as f:
        #     f.write(audio.get_wav_data())
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand your audio")
    except sr.RequestError as e:
        print("Google Speech Recognition error: {0}".format(e))
    except KeyboardInterrupt:
        print("Recording interrupted")

    with open("home/transcript.txt",'w') as f:
        f.write("")
    with open("home/transcript.txt",'a') as f:
        for items in answers:
            f.write(str(items['id'])+'#'+items['answer']+'\n')

    print("Recording completed.")

def screening(questions):
    p1 = multiprocessing.Process(target=record_video, args=(questions,))
    p2 = multiprocessing.Process(target=record_audio, args=(questions,))

    # Start the processes
    p1.start()
    p2.start()

    # Wait for the processes to finish
    p1.join()
    p2.join()


