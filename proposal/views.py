
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status

# views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import Proposal, Ambiguity, Discrepancy
from .serializers import ProposalSerializer, AmbiguitySerializer, DiscrepancySerializer, UwquestionsSerializer

from . import llm
from django.middleware.csrf import get_token

import os
import json
from datetime import datetime
import re

from dotenv import load_dotenv

# All model calls go through proposal/llm.py (Vertex AI by default, see .env).
load_dotenv()




def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def parse_json_response(raw_response: str | dict) -> dict:
    """
    Parses a JSON response (with optional 'json' or ```json prefix) 
    and returns it as a nested dictionary.
    
    Args:
        raw_response: Either a raw string (possibly prefixed with 'json' or ```json```) 
                      or an already-parsed dict.
    
    Returns:
        Nested dictionary as-is from the JSON.
    """
    
    if isinstance(raw_response, dict):
        return raw_response

    if isinstance(raw_response, str):
        # Strip ```json ... ``` or bare 'json' word prefix
        cleaned = re.sub(r'^```json\s*|^json\s*|```\s*$', '', raw_response.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)

    raise TypeError(f"Expected str or dict, got {type(raw_response).__name__}")



###################################################################################


class ProposalViewSet(viewsets.ModelViewSet):
    # Holds applicants' health answers: staff only. The public front end does not use these routes.
    permission_classes = [IsAdminUser]
    queryset = Proposal.objects.all().order_by('-created_at')
    serializer_class = ProposalSerializer

class AmbiguityViewSet(viewsets.ModelViewSet):
    # Holds applicants' health answers: staff only. The public front end does not use these routes.
    permission_classes = [IsAdminUser]
    queryset = Ambiguity.objects.all().order_by('-created_at')
    serializer_class = AmbiguitySerializer

class DiscrepancyViewSet(viewsets.ModelViewSet):
    # Holds applicants' health answers: staff only. The public front end does not use these routes.
    permission_classes = [IsAdminUser]
    queryset = Discrepancy.objects.all().order_by('-created_at')
    serializer_class = DiscrepancySerializer
    

###################################################################################


class findambiguity(APIView):
    def post(self, request):
        print("\n\n","findAmbiguity: request.data**=", request.data,"\n\n")
        applicant_prompt = request.data
        applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

        with open("find_ambiguity_instructions_v0.02.txt", "r", encoding="utf-8") as f:
            system_instructions = f.read()

        # 1. Fetch today's date dynamically and format it clearly (e.g., "February 26, 2026")
        today_date = datetime.now().strftime("%B %d, %Y")

        # 2. Create a small string to inject the date context
        date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

        # 3. Combine them all together
        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + applicant_prompt_str
#        print("Get Clarity Full prompt sent to Google Gen AI:\n", full_prompt)  # Debug: Check the final prompt being sent
        try:
            generated_text, usage = llm.generate_with_usage(full_prompt, model=llm.fast_model(), temperature=0.3, json_mode=True, label="Ambiguity check")
###############################################################
            generated_text_flat = parse_json_response(generated_text)
###############################################################
            print("\n\findambiguity - Google Gen AI response: ", generated_text_flat)
#            return JsonResponse({"response": generated_text}, safe=False)
            return JsonResponse({"response": generated_text_flat, "usage": usage}, safe=False)


        except Exception as e:
            print(f"Error occurred while calling the model: {e}")
            return JsonResponse({"error": str(e)}, status=llm.status_for(e))
        


###################################################################################



class getclarity(APIView):
# Create your views here.
    def post(self, request):
        print("\n\n","getClarity: request.data**=", request.data,"\n\n")
        applicant_prompt = request.data
        applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

        with open("Get_clarity_instructions_v0.07.txt", "r", encoding="utf-8") as f:
            system_instructions = f.read()

        # 1. Fetch today's date dynamically and format it clearly (e.g., "February 26, 2026")
        today_date = datetime.now().strftime("%B %d, %Y")

        # 2. Create a small string to inject the date context
        date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

        # 3. Combine them all together
        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + applicant_prompt_str
#        print("Get Clarity Full prompt sent to Google Gen AI:\n", full_prompt)  # Debug: Check the final prompt being sent
        try:
            generated_text, usage = llm.generate_with_usage(full_prompt, model=llm.fast_model(), temperature=0.3, json_mode=True, label="Discrepancy check")


###############################################################
            generated_text_flat = parse_json_response(generated_text)
###############################################################
            print("\n\ngetclarity - Google Gen AI response: ", generated_text_flat)
#            return JsonResponse({"response": generated_text}, safe=False)
            return JsonResponse({"response": generated_text_flat, "usage": usage}, safe=False)


        except Exception as e:
            print(f"Error occurred while calling the model: {e}")
            return JsonResponse({"error": str(e)}, status=llm.status_for(e))



########submit Updated ###############################################################################
class submit(APIView):
    # permission_classes = [IsAuthenticated]
    print("submit hit!")

    def post(self, request):
        print("\n\n","Submit Proposal form: request.data**=", request.data,"\n\n")
        applicant_prompt = request.data
        applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

        try:
            with open("Refined_system_instructions_v0.03.txt", "r", encoding="utf-8") as f:
                system_instructions = f.read()
        except FileNotFoundError:
            return JsonResponse({"error": "System instructions file not found."}, status=500)

        # 1. Fetch today's date dynamically and format it clearly
        today_date = datetime.now().strftime("%B %d, %Y")

        # 2. Create a small string to inject the date context
        date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

        # 3. Combine them all together
        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + applicant_prompt_str
        
        try:
            generated_text, usage = llm.generate_with_usage(full_prompt, model=llm.decision_model(), temperature=0.3, json_mode=True, label="Underwriting decision")


            ###############################################################
            # Since we used response_mime_type="application/json", it should be clean JSON.
            # You can still use your parse_json_response if it handles extra cleaning.
            generated_text_flat = parse_json_response(generated_text)
            ###############################################################
            print(" Submit Proposal - Google Gen AI response: ", generated_text_flat)

            # ==============================================================
            # NEW CODE: SAVE TO DATABASE USING SERIALIZER
            # ==============================================================
            
            # Map the data to fit your ProposalSerializer expected fields.
            # Note: Assuming 'age' and 'gender' are provided in request.data.
            # If not, provide default fallbacks to prevent database validation errors.
            db_payload = {
                "age": applicant_prompt.get("age", 0),  
                "gender": applicant_prompt.get("gender", "U"),
                "proposal_data": applicant_prompt,  # <--- This saves the original prompt!
                "response_data": generated_text_flat,  # <--- This saves the original response!
                "underwriting_decision": generated_text_flat.get("underwriting_decision"),
                "identified_health_profile": generated_text_flat.get("identified_health_profile"),
                "decision_rationale": generated_text_flat.get("decision_rationale"),
                "waiting_period_details": generated_text_flat.get("waiting_period_details"),
                "refer_to_uwr_details": generated_text_flat.get("refer_to_uwr_details"),
                "more_questions_details": generated_text_flat.get("more_questions_details"),
            }

            # Pass payload to serializer
            serializer = ProposalSerializer(data=db_payload)
            
            if serializer.is_valid():
                # Saves the Proposal to the DB
                saved_proposal = serializer.save() 
                
                # Construct the final API response
                api_response = {
                    "proposal_id": saved_proposal.id, # The frontend MUST save this ID
                    "response": generated_text_flat,
                    "usage": usage,
                }
                return JsonResponse(api_response, safe=False)
            else:
                print("Serializer Errors:", serializer.errors)
                return JsonResponse(
                    {"error": "Failed to save proposal to DB.", "details": serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            # ==============================================================

        except Exception as e:
            print(f"Error occurred while calling the model: {e}")
            return JsonResponse({"error": str(e)}, status=llm.status_for(e))
#######################################################################################        



class SubmitAdditionalAnswers(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        print("Submit Additional Answers hit!")

        data = request.data
        proposal_id = data.get("proposal_id")
        if not proposal_id:
            return JsonResponse({"error": "proposal_id is required"}, status=400)

        # 1. Retrieve the saved proposal from DB
        try:
            proposal = Proposal.objects.get(pk=proposal_id)
        except Proposal.DoesNotExist:
            return JsonResponse({"error": f"Proposal with id {proposal_id} not found"}, status=404)

        # 2. Get the stored proposal_data and response_data
        original_prompt = proposal.proposal_data or {}
        ai_first_response = proposal.response_data or {}

        # 3. Get the new additional answers from frontend
        additional_answers = data.get("additional_answers", [])

        # Convert to pretty JSON strings for prompt construction
        original_prompt_str = json.dumps(original_prompt, indent=2)
        ai_first_response_str = json.dumps(ai_first_response, indent=2)
        additional_answers_str = json.dumps(additional_answers, indent=2)

        # 4. Read system instructions
        try:
            with open("Add_Ans_system_instructions_v0.01.txt", "r", encoding="utf-8") as f:
                system_instructions = f.read()
        except FileNotFoundError:
            return JsonResponse({"error": "System instructions file not found."}, status=500)

        # 5. Setup Date Injection
        today_date = datetime.now().strftime("%B %d, %Y")
        date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

        # 6. Construct the combined context
        combined_context = f"""
--- ORIGINAL APPLICATION DATA ---
{original_prompt_str}

--- YOUR PREVIOUS ASSESSMENT ---
{ai_first_response_str}

--- NEW INFORMATION: APPLICANT'S ADDITIONAL ANSWERS ---
{additional_answers_str}
        """

        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + combined_context
        #print("Full follow-up prompt sent to Gen AI:\n", full_prompt)

        try:
            generated_text, usage = llm.generate_with_usage(full_prompt, model=llm.decision_model(), temperature=0.3, json_mode=True, label="Follow-up review")

            # Parse JSON response
            generated_text_flat = json.loads(generated_text)

            print("Follow-up Submit - Google Gen AI response: ", generated_text_flat)
            return JsonResponse({"response": generated_text_flat, "usage": usage}, safe=False)

        except Exception as e:
            print(f"Error occurred while calling the model: {e}")
            return JsonResponse({"error": str(e)}, status=llm.status_for(e))
        
        
class postUWQn(APIView):
    # permission_classes = [IsAuthenticated]
    def post(self, request):
        print("postUWQn hit!")
        print("\n\n", "postUWQn: request.data**=", request.data, "\n\n")

        data = request.data
        proposal_id = data.get("proposal_id")
        answers = data.get("answers")
        
        print(f"Received proposal_id: {proposal_id}")
        print(f"Received answers: {answers}")

        db_payload = {
            "answers": answers,
            "proposal": proposal_id
        }
        try:
            # Pass payload to serializer
            serializer = UwquestionsSerializer(data=db_payload)

            if serializer.is_valid():
                # Saves the Uwquestions record to the DB
                saved_question = serializer.save()

                # Construct the final API response
                api_response = {
                    "uwquestion_id": saved_question.id,
                    "proposal_id": saved_question.proposal_id,
                    "answers": saved_question.answers,
                }
                return JsonResponse(api_response, safe=False)

            else:
                print("Serializer Errors:", serializer.errors)
                return JsonResponse(
                    {
                        "error": "Failed to save Uwquestions to DB.",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            print(f"Error occurred while saving Uwquestions: {e}")
            return JsonResponse({"error": str(e)}, status=500)
#######################################################################################        


#######################################################################################
# Medical records upload: Document AI (OCR) -> Gemini (map to questionnaire) -> prefill

MAX_RECORD_FILES = 8
MAX_RECORD_TEXT_CHARS = 120_000  # total OCR text sent to Gemini


class extractrecords(APIView):
    """multipart/form-data with one or more `files`. Nothing is stored: files and
    OCR text live only for the duration of the request."""

    def post(self, request):
        from . import docai, records
        from django.conf import settings

        uploads = request.FILES.getlist("files")
        if not uploads:
            return JsonResponse({"error": "No files uploaded."}, status=400)
        if len(uploads) > MAX_RECORD_FILES:
            return JsonResponse({"error": f"Upload at most {MAX_RECORD_FILES} files at a time."}, status=400)

        guessed = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                   ".png": "image/png", ".tif": "image/tiff", ".tiff": "image/tiff", ".webp": "image/webp"}
        file_results, doc_blocks, total_chars = [], [], 0
        for f in uploads:
            mime = f.content_type if f.content_type in docai.ALLOWED_MIME_TYPES else \
                guessed.get(os.path.splitext(f.name)[1].lower())
            if mime is None:
                return JsonResponse({"error": f"Unsupported file type: {f.name}. Use PDF, JPG, PNG, TIFF or WebP."}, status=400)
            if f.size > docai.MAX_FILE_BYTES:
                return JsonResponse({"error": f"{f.name} is larger than 20 MB."}, status=400)
            try:
                text, pages = docai.extract_text(f.read(), mime)
            except docai.DocAINotConfigured as e:
                return JsonResponse({"error": str(e)}, status=503)
            except docai.DocAIError as e:
                print(f"Document AI failed for {f.name}: {e}")
                return JsonResponse({"error": f"Document AI could not read {f.name}: {e}"}, status=502)

            file_results.append({"file_name": f.name, "pages": pages, "characters": len(text)})
            if text.strip():
                total_chars += len(text)
                doc_blocks.append(f"=== DOCUMENT: {f.name} ===\n{text}")

        if not doc_blocks:
            return JsonResponse({"error": "No readable text was found in the uploaded files.", "files": file_results}, status=422)
        if total_chars > MAX_RECORD_TEXT_CHARS:
            return JsonResponse({"error": "The uploaded records are too long to process together. Upload fewer or shorter documents."}, status=413)

        docai_usage = llm.docai_usage(sum(f["pages"] for f in file_results))

        with open(os.path.join(settings.BASE_DIR, "Extract_records_instructions_v0.01.txt"), "r", encoding="utf-8") as fh:
            system_instructions = fh.read()
        today = datetime.now()
        date_injection = f"SYSTEM NOTE: Today's current date is {today.strftime('%B %d, %Y')}."
        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + "\n\n".join(doc_blocks)

        try:
            text, usage = llm.generate_with_usage(full_prompt, model=llm.decision_model(), temperature=0.1, json_mode=True, label="Records mapping")
            raw = parse_json_response(text)
            if not isinstance(raw, dict):
                raise ValueError("Model returned a non-object response.")
        except Exception as e:
            print(f"Error mapping records to the questionnaire: {e}")
            return JsonResponse({"error": f"Could not interpret the records: {e}"}, status=llm.status_for(e))

        return JsonResponse({"prefill": records.build_prefill(raw, today.date()), "files": file_results, "usage": [docai_usage, usage]})
