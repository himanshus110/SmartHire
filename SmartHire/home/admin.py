from django.contrib import admin
from .models import Job, Resume, QuestionBank, CandidateResponse
# Register your models here.

admin.site.register(Job)
admin.site.register(Resume)
admin.site.register(QuestionBank)
admin.site.register(CandidateResponse)
