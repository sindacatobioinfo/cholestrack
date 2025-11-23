"""
Views for AI Agent chat interface and analysis.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings
from pathlib import Path

from users.decorators import role_confirmed_required
from .models import ChatSession, ChatMessage, AnalysisJob
from .gemini_client import GeminiAnalysisClient, DataAnonymizer
from .tasks import run_statistical_analysis, run_genetic_model_analysis, run_comparative_analysis
from .tsv_loader import load_tsv_preview, format_dataframe_for_ai
from files.models import AnalysisFileLocation


@login_required
@role_confirmed_required
def chat_interface(request):
    """
    Main chat interface view.
    """
    # Get or create active session
    active_session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if not active_session:
        active_session = ChatSession.objects.create(
            user=request.user,
            title="New Conversation"
        )

    # Get recent sessions for sidebar
    recent_sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by('-updated_at')[:10]

    # Get messages for active session
    messages_list = active_session.messages.all()

    context = {
        'active_session': active_session,
        'recent_sessions': recent_sessions,
        'messages': messages_list,
        'title': 'AI Analysis Agent'
    }

    return render(request, 'ai_agent/chat_interface.html', context)


@login_required
@role_confirmed_required
@require_http_methods(["POST"])
def send_message(request):
    """
    Send a message to the AI agent (AJAX endpoint).
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        message_content = data.get('message', '').strip()

        if not message_content:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)

        # Get or create session
        if session_id:
            session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        else:
            session = ChatSession.objects.create(user=request.user)

        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=message_content
        )

        # Update session title from first message
        if session.messages.count() == 1:
            session.update_title_from_first_message()

        # Build conversation history (limit to last 10 messages for context window)
        # This prevents infinite history growth and API token limits
        conversation_history = []
        recent_messages = session.messages.filter(
            role__in=['user', 'assistant']
        ).order_by('-created_at')[:10]  # Get last 10 messages

        # Reverse to maintain chronological order
        for msg in reversed(recent_messages):
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })

        # Get available samples with file locations
        # No limit - show ALL samples so AI can reference any of them
        available_samples_qs = AnalysisFileLocation.objects.filter(
            file_type='TSV',
            is_active=True
        ).values('sample_id', 'file_path', 'data_type').distinct()

        # No need to anonymize - sample_id in database is already anonymized
        sample_id_map = {}  # Keep empty map for compatibility with existing code

        # Build sample list with file information
        sample_list = list(available_samples_qs)
        sample_ids = [s['sample_id'] for s in sample_list]

        # Prepare variant data summary with ALL samples
        variant_data_summary = f"Available samples for analysis ({len(sample_ids)} total):\n\n"
        for sample in sample_list:
            variant_data_summary += f"- {sample['sample_id']} ({sample['data_type']})\n"

        variant_data_summary += "\nYou can query any of these samples. When a user asks about a specific sample, "
        variant_data_summary += "I will load the variant data from the corresponding TSV file for analysis.\n"

        # Check if user mentions specific sample IDs in their message
        # If so, load preview data from those TSV files
        mentioned_samples = []
        for sample_id in sample_ids:
            if sample_id.lower() in message_content.lower():
                mentioned_samples.append(sample_id)

        # Load data previews for mentioned samples
        if mentioned_samples:
            variant_data_summary += "\n" + "="*60 + "\n"
            variant_data_summary += "VARIANT DATA PREVIEWS (first 5 rows):\n"
            variant_data_summary += "="*60 + "\n\n"

            for sample_id in mentioned_samples[:3]:  # Limit to 3 samples to avoid overwhelming context
                # Get file path for this sample
                sample_file = next((s for s in sample_list if s['sample_id'] == sample_id), None)
                if sample_file:
                    # Construct full file path - files are in /media/remote_files/
                    relative_path = sample_file['file_path']
                    file_path = f"/media/remote_files/{relative_path}"

                    # Load preview of the TSV file
                    df, error = load_tsv_preview(file_path, num_rows=5)

                    if df is not None:
                        variant_data_summary += f"Sample: {sample_id}\n"
                        variant_data_summary += f"File: {Path(file_path).name}\n"
                        variant_data_summary += f"Total columns: {len(df.columns)}\n\n"
                        variant_data_summary += format_dataframe_for_ai(df, max_cols=40)
                        variant_data_summary += "\n\n" + "-"*60 + "\n\n"
                    else:
                        variant_data_summary += f"Sample: {sample_id}\n"
                        variant_data_summary += f"Error loading data: {error}\n\n"

        # Call Gemini API
        try:
            gemini_client = GeminiAnalysisClient()
            response = gemini_client.analyze_variant_question(
                question=message_content,
                variant_data_summary=variant_data_summary,
                conversation_history=conversation_history[:-1],  # Exclude current message
                sample_id_map=sample_id_map
            )

            # Save assistant response
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=response['content'],
                tokens_used=response['tokens_used']
            )

            # Update session token count
            session.total_tokens_used += response['tokens_used']
            session.save()

            return JsonResponse({
                'success': True,
                'message_id': str(assistant_message.message_id),
                'content': response['content'],
                'tokens_used': response['tokens_used'],
                'session_id': str(session.session_id)
            })

        except Exception as e:
            # Log error and return user-friendly message
            error_msg = f"I apologize, but I encountered an error processing your request: {str(e)}"

            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=error_msg
            )

            return JsonResponse({
                'success': True,  # Still return success to show the error message
                'message_id': str(assistant_message.message_id),
                'content': error_msg,
                'session_id': str(session.session_id)
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_confirmed_required
@require_http_methods(["POST"])
def start_analysis_job(request):
    """
    Start a background analysis job (AJAX endpoint).
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        job_type = data.get('job_type')
        parameters = data.get('parameters', {})
        sample_ids = data.get('sample_ids', [])

        if not session_id or not job_type:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)

        # Create analysis job
        job = AnalysisJob.objects.create(
            session=session,
            job_type=job_type,
            parameters=parameters,
            sample_ids=sample_ids,
            status='PENDING'
        )

        # Start appropriate Celery task
        if job_type == 'STATISTICAL':
            task = run_statistical_analysis.delay(str(job.job_id))
        elif job_type == 'GENETIC_MODEL':
            task = run_genetic_model_analysis.delay(str(job.job_id))
        elif job_type == 'COMPARATIVE':
            task = run_comparative_analysis.delay(str(job.job_id))
        else:
            return JsonResponse({'error': 'Unknown job type'}, status=400)

        # Create a system message about the job
        ChatMessage.objects.create(
            session=session,
            role='system',
            content=f"Started {job.get_job_type_display()} analysis (Job ID: {job.job_id})",
            has_analysis_job=True,
            metadata={'job_id': str(job.job_id)}
        )

        return JsonResponse({
            'success': True,
            'job_id': str(job.job_id),
            'job_type': job.get_job_type_display()
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_confirmed_required
def job_status(request, job_id):
    """
    Check status of an analysis job (AJAX endpoint).
    """
    job = get_object_or_404(AnalysisJob, job_id=job_id, session__user=request.user)

    response_data = {
        'job_id': str(job.job_id),
        'status': job.status,
        'job_type': job.get_job_type_display(),
        'created_at': job.created_at.isoformat(),
    }

    if job.status == 'COMPLETED':
        response_data['completed_at'] = job.completed_at.isoformat()
        response_data['result_data'] = job.result_data
        if job.result_file_path:
            response_data['has_report'] = True
            response_data['report_type'] = job.result_file_type
            response_data['download_url'] = f"/ai-agent/download-report/{job.job_id}/"

    elif job.status == 'FAILED':
        response_data['error_message'] = job.error_message

    return JsonResponse(response_data)


@login_required
@role_confirmed_required
def download_report(request, job_id):
    """
    Download generated report file.
    """
    job = get_object_or_404(AnalysisJob, job_id=job_id, session__user=request.user)

    if job.status != 'COMPLETED' or not job.result_file_path:
        raise Http404("Report not available")

    file_path = Path(job.result_file_path)
    if not file_path.exists():
        raise Http404("Report file not found")

    # Determine content type
    content_types = {
        'html': 'text/html',
        'csv': 'text/csv',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    content_type = content_types.get(job.result_file_type, 'application/octet-stream')

    # Stream file response
    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type,
        as_attachment=True,
        filename=file_path.name
    )

    return response


@login_required
@role_confirmed_required
def new_session(request):
    """
    Create a new chat session.
    """
    session = ChatSession.objects.create(
        user=request.user,
        title="New Conversation"
    )

    return redirect('ai_agent:chat_interface')


@login_required
@role_confirmed_required
def load_session(request, session_id):
    """
    Load a specific chat session.
    """
    session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)

    # Mark as active session
    ChatSession.objects.filter(user=request.user).update(is_active=False)
    session.is_active = True
    session.save()

    return redirect('ai_agent:chat_interface')
