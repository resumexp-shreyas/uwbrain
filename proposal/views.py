
from django.http import JsonResponse
from rest_framework.views import APIView

# views.py
from rest_framework import viewsets
from .models import Proposal, Ambiguity, Discrepancy
from .serializers import ProposalSerializer, AmbiguitySerializer, DiscrepancySerializer, UwquestionsSerializer

import google.generativeai as genai# After
from django.middleware.csrf import get_token

import google.auth # Import Google's authentication library # After
import json
from datetime import datetime

def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})

class getclarity(APIView):
# Create your views here.
    def post(self, request):
        print("\n\n","getClarity: request.data**=", request.data,"\n\n")
        applicant_prompt = request.data
        applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

        with open("Get_clarity_instructions_v0.06.txt", "r", encoding="utf-8") as f:
            system_instructions = f.read()

        # 1. Fetch today's date dynamically and format it clearly (e.g., "February 26, 2026")
        today_date = datetime.now().strftime("%B %d, %Y")

        # 2. Create a small string to inject the date context
        date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

        # 3. Combine them all together
        full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + applicant_prompt_str
#        print("Get Clarity Full prompt sent to Google Gen AI:\n", full_prompt)  # Debug: Check the final prompt being sent
        try:
            credentials, project = google.auth.default()
            if credentials:
                genai.configure(credentials=credentials)

            # Use the model name you confirmed from list_models()
            #model = genai.GenerativeModel('models/gemini-2.5-pro')
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
##                max_output_tokens=2000,
            )

            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            generated_text = ""
            if response.candidates:
                if hasattr(response.candidates[0].content, 'text'):
                     generated_text = response.candidates[0].content.text
                else:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
            else:
                finish_reason = None
                safety_ratings = []
                if response.prompt_feedback:
                    finish_reason = response.prompt_feedback.block_reason
                    # Access safety ratings if available
                    if response.prompt_feedback.safety_ratings:
                         safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]
                
                error_message = f"Model did not return any candidates."
                if finish_reason:
                    error_message += f" Block Reason: {finish_reason}."
                if safety_ratings:
                    error_message += f" Safety Ratings: {safety_ratings}."
                
                raise Exception(error_message)


###############################################################
            generated_text_flat = parse_json_response(generated_text)
###############################################################
            print("\n\ngetclarity - Google Gen AI response: ", generated_text_flat)
#            return JsonResponse({"response": generated_text}, safe=False)
            return JsonResponse({"response": generated_text_flat}, safe=False)


        except Exception as e:
            print(f"Error occurred while calling Google Gen AI: {e}")
            return JsonResponse({"error": str(e)}, status=500)


# class submit(APIView):
# #    permission_classes = [IsAuthenticated]
#     print("submit hit!")

#     def post(self, request):
#         print("\n\n","Submit Proposal form: request.data**=", request.data,"\n\n")
#         applicant_prompt = request.data
#         applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

#         with open("Refined_system_instructions_v0.02.txt", "r", encoding="utf-8") as f:
#             system_instructions = f.read()

#         # 1. Fetch today's date dynamically and format it clearly (e.g., "February 26, 2026")
#         today_date = datetime.now().strftime("%B %d, %Y")

#         # 2. Create a small string to inject the date context
#         date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

#         # 3. Combine them all together
#         full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + applicant_prompt_str
#         ##print("Submition- Full prompt sent to Google Gen AI:\n", full_prompt)  # Debug: Check the final prompt being sent
#         try:
#             credentials, project = google.auth.default()
#             if credentials:
#                 genai.configure(credentials=credentials)

#             # Use the model name you confirmed from list_models()
#             #model = genai.GenerativeModel('models/gemini-2.5-pro')
#             model = genai.GenerativeModel("models/gemini-2.5-pro")

#             generation_config = genai.types.GenerationConfig(
#                 temperature=0.3,
# ##                max_output_tokens=2000,
#             )

#             response = model.generate_content(
#                 full_prompt,
#                 generation_config=generation_config,
#             )

#             generated_text = ""
#             if response.candidates:
#                 if hasattr(response.candidates[0].content, 'text'):
#                      generated_text = response.candidates[0].content.text
#                 else:
#                     for part in response.candidates[0].content.parts:
#                         if hasattr(part, 'text'):
#                             generated_text += part.text
#             else:
#                 finish_reason = None
#                 safety_ratings = []
#                 if response.prompt_feedback:
#                     finish_reason = response.prompt_feedback.block_reason
#                     # Access safety ratings if available
#                     if response.prompt_feedback.safety_ratings:
#                          safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]
                
#                 error_message = f"Model did not return any candidates."
#                 if finish_reason:
#                     error_message += f" Block Reason: {finish_reason}."
#                 if safety_ratings:
#                     error_message += f" Safety Ratings: {safety_ratings}."
                
#                 raise Exception(error_message)


# ###############################################################
#             generated_text_flat = parse_json_response(generated_text)
# ###############################################################
#             print(" Submit Proposal - Google Gen AI response: ", generated_text_flat)
# #            return JsonResponse({"response": generated_text}, safe=False)
#             return JsonResponse({"response": generated_text_flat}, safe=False)


#         except Exception as e:
#             print(f"Error occurred while calling Google Gen AI: {e}")
#             return JsonResponse({"error": str(e)}, status=500)   
###############################################################################

# import json
# from datetime import datetime
# from rest_framework.views import APIView
# from django.http import JsonResponse
# from rest_framework.response import Response
from rest_framework import status
# import google.auth
# import google.generativeai as genai

# Make sure to import your serializer
# from .serializers import ProposalSerializer
# from .utils import parse_json_response

########submit Updated ###############################################################################
class submit(APIView):
    # permission_classes = [IsAuthenticated]
    print("submit hit!")

    def post(self, request):
        print("\n\n","Submit Proposal form: request.data**=", request.data,"\n\n")
        applicant_prompt = request.data
        applicant_prompt_str = json.dumps(applicant_prompt, indent=2)

        try:
            with open("Refined_system_instructions_v0.02.txt", "r", encoding="utf-8") as f:
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
            credentials, project = google.auth.default()
            if credentials:
                genai.configure(credentials=credentials)

            model = genai.GenerativeModel("models/gemini-2.5-pro")

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                # Enforce JSON output straight from the model
                response_mime_type="application/json",
            )

            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            generated_text = ""
            if response.candidates:
                if hasattr(response.candidates[0].content, 'text'):
                     generated_text = response.candidates[0].content.text
                else:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
            else:
                finish_reason = None
                safety_ratings = []
                if response.prompt_feedback:
                    finish_reason = response.prompt_feedback.block_reason
                    if response.prompt_feedback.safety_ratings:
                         safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]
                
                error_message = f"Model did not return any candidates."
                if finish_reason:
                    error_message += f" Block Reason: {finish_reason}."
                if safety_ratings:
                    error_message += f" Safety Ratings: {safety_ratings}."
                
                raise Exception(error_message)


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
                    "response": generated_text_flat
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
            print(f"Error occurred while calling Google Gen AI: {e}")
            return JsonResponse({"error": str(e)}, status=500)
#######################################################################################        
        
import json
import re


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
            credentials, project = google.auth.default()
            if credentials:
                genai.configure(credentials=credentials)

            # Use the model name you confirmed from list_models()
            #model = genai.GenerativeModel('models/gemini-2.5-pro')
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
##                max_output_tokens=2000,
            )

            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            generated_text = ""
            if response.candidates:
                if hasattr(response.candidates[0].content, 'text'):
                     generated_text = response.candidates[0].content.text
                else:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
            else:
                finish_reason = None
                safety_ratings = []
                if response.prompt_feedback:
                    finish_reason = response.prompt_feedback.block_reason
                    # Access safety ratings if available
                    if response.prompt_feedback.safety_ratings:
                         safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]
                
                error_message = f"Model did not return any candidates."
                if finish_reason:
                    error_message += f" Block Reason: {finish_reason}."
                if safety_ratings:
                    error_message += f" Safety Ratings: {safety_ratings}."
                
                raise Exception(error_message)
###############################################################
            generated_text_flat = parse_json_response(generated_text)
###############################################################
            print("\n\findambiguity - Google Gen AI response: ", generated_text_flat)
#            return JsonResponse({"response": generated_text}, safe=False)
            return JsonResponse({"response": generated_text_flat}, safe=False)


        except Exception as e:
            print(f"Error occurred while calling Google Gen AI: {e}")
            return JsonResponse({"error": str(e)}, status=500)
        



import json
from datetime import datetime
from rest_framework.views import APIView
from django.http import JsonResponse
import google.auth
import google.generativeai as genai

# Assuming you have this helper function defined somewhere
# from .utils import parse_json_response 

# class SubmitAdditionalAnswers(APIView): #without retriving function.
#     # permission_classes = [IsAuthenticated]

#     def post(self, request):
#         print("Submit Additional Answers hit!")
        
#         # Expected frontend payload:
#         # {
#         #   "original_prompt": {...},
#         #   "ai_first_response": {...},
#         #   "additional_answers": [{"question": "...", "answer": "..."}, ...]
#         # }
#         data = request.data

#         proposal_id= data.get("proposal_id")  # The frontend MUST send the proposal_id to link the follow-up to the original proposal        
#         original_prompt_str = json.dumps(data.get("original_prompt", {}), indent=2)
#         ai_first_response_str = json.dumps(data.get("ai_first_response", {}), indent=2)
        
#         additional_answers_str = json.dumps(data.get("additional_answers", []), indent=2)

#         # 1. Read the NEW version of system instructions
#         try:
#             with open("Add_Ans_system_instructions_v0.01.txt", "r", encoding="utf-8") as f:
#                 system_instructions = f.read()
#         except FileNotFoundError:
#             return JsonResponse({"error": "System instructions file not found."}, status=500)

#         # 2. Setup Date Injection
#         today_date = datetime.now().strftime("%B %d, %Y")
#         date_injection = f"SYSTEM NOTE: Today's current date is {today_date}. Use this date to determine if any years provided are in the past or the future."

#         # 3. Construct the "Memory" Prompt
#         # By providing the history explicitly inside a single prompt, Gemini perfectly 
#         # understands the context without needing a complex multi-turn ChatSession object.
#         combined_context = f"""
# --- ORIGINAL APPLICATION DATA ---
# {original_prompt_str}

# --- YOUR PREVIOUS ASSESSMENT ---
# {ai_first_response_str}

# --- NEW INFORMATION: APPLICANT'S ADDITIONAL ANSWERS ---
# {additional_answers_str}
#         """

#         full_prompt = system_instructions + "\n\n" + date_injection + "\n\n" + combined_context
#         print("Full follow-up prompt sent to Gen AI:\n", full_prompt)

#         try:
#             credentials, project = google.auth.default()
#             if credentials:
#                 genai.configure(credentials=credentials)

#             model = genai.GenerativeModel("models/gemini-2.5-pro")

#             generation_config = genai.types.GenerationConfig(
#                 temperature=0.3,
#                 # Set response_mime_type to guarantee valid JSON structure!
#                 response_mime_type="application/json", 
#             )

#             response = model.generate_content(
#                 full_prompt,
#                 generation_config=generation_config,
#             )

#             generated_text = ""
#             if response.candidates:
#                 if hasattr(response.candidates[0].content, 'text'):
#                    generated_text = response.candidates[0].content.text
#                 else:
#                   for part in response.candidates[0].content.parts:
#                     if hasattr(part, 'text'):
#                       generated_text += part.text
#             else:
#                 finish_reason = None
#                 safety_ratings = []
#                 if response.prompt_feedback:
#                     finish_reason = response.prompt_feedback.block_reason
#                     if response.prompt_feedback.safety_ratings:
#                          safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]
                   
#                 error_message = f"Model did not return any candidates."
#                 if finish_reason:
#                     error_message += f" Block Reason: {finish_reason}."
#                 if safety_ratings:
#                     error_message += f" Safety Ratings: {safety_ratings}."
                   
#                 raise Exception(error_message)

#             # Flatting/parsing the JSON (using your existing function)
#             # generated_text_flat = parse_json_response(generated_text)
            
#             # Since we added response_mime_type="application/json", generated_text is guaranteed to be a JSON string.
#             generated_text_flat = json.loads(generated_text)

#             print(" Follow-up Submit - Google Gen AI response: ", generated_text_flat)
#             return JsonResponse({"response": generated_text_flat}, safe=False)

#         except Exception as e:
#             print(f"Error occurred while calling Google Gen AI: {e}")
#             return JsonResponse({"error": str(e)}, status=500)



class ProposalViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.all().order_by('-created_at')
    serializer_class = ProposalSerializer

class AmbiguityViewSet(viewsets.ModelViewSet):
    queryset = Ambiguity.objects.all().order_by('-created_at')
    serializer_class = AmbiguitySerializer

class DiscrepancyViewSet(viewsets.ModelViewSet):
    queryset = Discrepancy.objects.all().order_by('-created_at')
    serializer_class = DiscrepancySerializer
    


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
            credentials, project = google.auth.default()
            if credentials:
                genai.configure(credentials=credentials)

            model = genai.GenerativeModel("models/gemini-2.5-pro")

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            )

            response = model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            generated_text = ""
            if response.candidates:
                if hasattr(response.candidates[0].content, 'text'):
                    generated_text = response.candidates[0].content.text
                else:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
            else:
                finish_reason = None
                safety_ratings = []
                if response.prompt_feedback:
                    finish_reason = response.prompt_feedback.block_reason
                    if response.prompt_feedback.safety_ratings:
                        safety_ratings = [{sr.category: sr.probability} for sr in response.prompt_feedback.safety_ratings]

                error_message = f"Model did not return any candidates."
                if finish_reason:
                    error_message += f" Block Reason: {finish_reason}."
                if safety_ratings:
                    error_message += f" Safety Ratings: {safety_ratings}."
                raise Exception(error_message)

            # Parse JSON response
            generated_text_flat = json.loads(generated_text)

            print("Follow-up Submit - Google Gen AI response: ", generated_text_flat)
            return JsonResponse({"response": generated_text_flat}, safe=False)

        except Exception as e:
            print(f"Error occurred while calling Google Gen AI: {e}")
            return JsonResponse({"error": str(e)}, status=500)
        
        
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
