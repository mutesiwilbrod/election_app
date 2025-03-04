from django.shortcuts import render, redirect, HttpResponse

# Create your views here.
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.contrib.auth.decorators import login_required
from .serializers import ResultSerializer
from django.http import JsonResponse
from .models import Candidate, PollingStation
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from .models import Result, ElectionPosition, PollingStation, User
# tally/views.py
import json

from django.shortcuts import render, redirect
from django.db.models import Sum

# Import your models
from .models import Candidate, Result
# Generate JWT token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/admin/")  # Change this to your dashboard URL
        else:
            return HttpResponse("Invalid credentials. Try again.", status=401)

    return render(request, "login.html")
@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")
# Submit election results (Agent only)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_results(request):
    if request.user.role != 'superuser':
        return redirect('login')

    data = request.data
    polling_station = get_object_or_404(PollingStation, id=data.get('polling_station'))
    candidate = get_object_or_404(Candidate, id=data.get('candidate'))
    
    # Save result
    result = Result.objects.create(
        polling_station=polling_station,
        candidate=candidate,
        votes=data.get('votes'),
        agent=request.user
    )
    return Response({"message": "Result submitted successfully!"})
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        print("Attempting login for:", username)  # Debug
        user = authenticate(request, username=username, password=password)
        if user is not None:
            print("Login successful for:", username)
            login(request, user)
            next_url = request.GET.get('next') or '/dashboard/'
            print("Redirecting to:", next_url)
            return redirect(next_url)
        else:
            print("Invalid credentials for:", username)
            return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

# tally/views.py
@login_required
def dashboard_view(request):
    # Ensure only superusers can view this dashboard
    if request.user.role != 'agent':
        return redirect('login')

    # Overall Election Performance
    total_votes = Result.objects.aggregate(total_votes=Sum('votes'))['total_votes'] or 0

    positions = ElectionPosition.objects.all()
    votes_by_position = []
    for pos in positions:
        # Sum votes for all candidates in this position
        candidates = pos.candidate_set.all()
        votes_sum = Result.objects.filter(candidate__in=candidates).aggregate(total=Sum('votes'))['total'] or 0
        votes_by_position.append({'position': pos.name, 'votes': votes_sum})

    # Latest (real-time) results: get the 10 most recent entries
    latest_results = Result.objects.order_by('-timestamp')[:10]

    # Agent Monitoring: List agents with their stats
    agents = User.objects.filter(role='agent')
    agent_stats = []
    for agent in agents:
        submitted_count = Result.objects.filter(agent=agent).count()
        # For simplicity, we assume corrections = 0 (you could add a field if needed)
        corrections = 0
        total_polling_stations = PollingStation.objects.filter(subcounty=agent.subcounty).count() if agent.subcounty else 0
        polling_with_results = Result.objects.filter(agent=agent).values('polling_station').distinct().count()
        coverage = (polling_with_results / total_polling_stations * 100) if total_polling_stations > 0 else 0
        agent_stats.append({
            'agent': agent.username,
            'submitted': submitted_count,
            'corrections': corrections,
            'coverage': round(coverage, 2)
        })

    # Subcounty & Polling Station Overview
    polling_stations = PollingStation.objects.all()
    subcounty_performance = {}
    for ps in polling_stations:
        status = 'Results Submitted' if Result.objects.filter(polling_station=ps).exists() else 'Results Pending'
        if ps.subcounty not in subcounty_performance:
            subcounty_performance[ps.subcounty] = {'total': 0, 'submitted': 0, 'results': []}
        subcounty_performance[ps.subcounty]['total'] += 1
        if status == 'Results Submitted':
            subcounty_performance[ps.subcounty]['submitted'] += 1
        subcounty_performance[ps.subcounty]['results'].append({
            'name': ps.name,
            'status': status,
        })

    # Prepare chart data for votes by position
    chart_data = {
        'positions': [entry['position'] for entry in votes_by_position],
        'votes': [entry['votes'] for entry in votes_by_position]
    }

    # Alerts and Notifications: e.g., agents not updating in the last hour
    alerts = []
    one_hour_ago = timezone.now() - timedelta(hours=1)
    for agent in agents:
        latest_update = Result.objects.filter(agent=agent).order_by('-timestamp').first()
        if not latest_update or latest_update.timestamp < one_hour_ago:
            alerts.append(f"Agent {agent.username} has not updated their results in the last hour.")

    context = {
        'total_votes': total_votes,
        'votes_by_position': votes_by_position,
        'latest_results': latest_results,
        'agent_stats': agent_stats,
        'subcounty_performance': subcounty_performance,
        'chart_data': chart_data,
        'alerts': alerts,
    }
    return render(request, "dashboard.html", context)
# tally/views.py

def generate_votes_chart_image(chart_data):
    """
    Generates a bar chart image for votes by candidate.
    chart_data should be a dict with keys: 'candidates', 'votes', and 'percentages'.
    """
    candidates = chart_data.get('candidates', [])
    votes = chart_data.get('votes', [])
    percentages = chart_data.get('percentages', [])

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(candidates))
    bars = ax.bar(x, votes, color='skyblue')
    
    # Annotate each bar with vote count and percentage
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height,
            f"{votes[i]} ({percentages[i]}%)",
            ha='center', va='bottom'
        )
    
    ax.set_xticks(x)
    ax.set_xticklabels(candidates, rotation=45, ha='right')
    ax.set_ylabel('Votes')
    ax.set_title('Votes by Candidate')
    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close(fig)
    chart_image = base64.b64encode(image_png).decode('utf-8')
    return chart_image

def generate_subcounty_chart_image(subcounty_data):
    """
    Generates a horizontal bar chart showing the percentage of polling stations submitted per subcounty.
    subcounty_data: dictionary mapping subcounty -> dict with keys 'total' and 'submitted'.
    """
    subcounties = list(subcounty_data.keys())
    percentages = []
    for subcounty in subcounties:
        total = subcounty_data[subcounty]['total']
        submitted = subcounty_data[subcounty]['submitted']
        percentage = (submitted / total * 100) if total > 0 else 0
        percentages.append(percentage)

    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(subcounties))
    ax.barh(y, percentages, color='green')
    ax.set_yticks(y)
    ax.set_yticklabels(subcounties)
    ax.set_xlabel("Submission Percentage (%)")
    ax.set_title("Subcounty Polling Station Submission Overview")
    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close(fig)
    chart_image = base64.b64encode(image_png).decode('utf-8')
    return chart_image

@login_required
def dashboard_view(request):
    # --- Votes by Candidate Chart ---
    candidates_qs = Candidate.objects.all()
    candidate_names = []
    candidate_votes = []
    candidate_photos = []  # For future use if needed
    for candidate in candidates_qs:
        candidate_names.append(candidate.name)
        candidate_photos.append(candidate.photo.url if candidate.photo else '')
        total_candidate_votes = (
            Result.objects.filter(candidate=candidate)
            .aggregate(total=Sum('votes'))['total'] or 0
        )
        candidate_votes.append(total_candidate_votes)
    
    total_votes = sum(candidate_votes)
    percentages = [round((v / total_votes * 100), 1) if total_votes > 0 else 0 for v in candidate_votes]
    votes_chart_data = {
        'candidates': candidate_names,
        'votes': candidate_votes,
        'percentages': percentages,
        'photos': candidate_photos,
    }
    chart_image = generate_votes_chart_image(votes_chart_data)

    # --- Subcounty & Polling Station Overview Chart ---
    polling_stations = PollingStation.objects.all()
    subcounty_performance = {}
    for ps in polling_stations:
        subcounty = ps.subcounty
        if subcounty not in subcounty_performance:
            subcounty_performance[subcounty] = {'total': 0, 'submitted': 0, 'results': []}
        subcounty_performance[subcounty]['total'] += 1
        if Result.objects.filter(polling_station=ps).exists():
            subcounty_performance[subcounty]['submitted'] += 1
        subcounty_performance[subcounty]['results'].append({
            'name': ps.name,
            'status': 'Submitted' if Result.objects.filter(polling_station=ps).exists() else 'Pending'
        })
    subcounty_chart_image = generate_subcounty_chart_image(subcounty_performance)

    # --- Real-time Results (Latest 10) ---
    latest_results = Result.objects.order_by('-timestamp')[:10]

    # --- Agent Monitoring ---
    # Example: Retrieve agents with their submission counts (customize as needed)
    agents = User.objects.filter(role='agent')
    agent_stats = []
    for agent in agents:
        submitted_count = Result.objects.filter(agent=agent).count()
        # For simplicity, assume corrections = 0
        corrections = 0
        total_polling = PollingStation.objects.filter(subcounty=agent.subcounty).count() if agent.subcounty else 0
        polling_with_results = Result.objects.filter(agent=agent).values('polling_station').distinct().count()
        coverage = (polling_with_results / total_polling * 100) if total_polling > 0 else 0
        agent_stats.append({
            'agent': agent.username,
            'submitted': submitted_count,
            'corrections': corrections,
            'coverage': round(coverage, 1)
        })

    context = {
        'total_votes': total_votes,
        'chart_image': chart_image,
        'subcounty_chart_image': subcounty_chart_image,
        'latest_results': latest_results,
        'agent_stats': agent_stats,
        'subcounty_performance': subcounty_performance,
    }
    return render(request, "dashboard.html", context)
# tally/views.py

@login_required
def submit_results_view(request):
    agent = request.user
    if request.method == "POST":
        polling_station_id = request.POST.get("polling_station")
        if not polling_station_id:
            return HttpResponse("Polling station is required.", status=400)
        try:
            polling_station = PollingStation.objects.get(id=polling_station_id)
        except PollingStation.DoesNotExist:
            return HttpResponse("Invalid polling station.", status=400)
        
        # Check if results already exist for this polling station by this agent.
        existing_results = Result.objects.filter(polling_station=polling_station, agent=agent)
        if existing_results.exists():
            # Redirect to the edit page with polling_station_id in query parameters.
            return redirect(f"/edit_results/?polling_station_id={polling_station.id}")
        
        candidate_ids = request.POST.getlist("candidate_ids[]")
        if not candidate_ids:
            return HttpResponse("No candidates found.", status=400)
        
        for candidate_id in candidate_ids:
            vote_input = request.POST.get(f"votes_{candidate_id}")
            try:
                votes = int(vote_input)
            except (TypeError, ValueError):
                votes = 0
            try:
                candidate = Candidate.objects.get(id=candidate_id)
            except Candidate.DoesNotExist:
                continue
            # Create new Result entries
            Result.objects.create(
                polling_station=polling_station,
                candidate=candidate,
                agent=agent,
                votes=votes
            )
        return redirect("dashboard")
    
    else:
        # GET request: render the submission form.
        election_positions = ElectionPosition.objects.all()
        # Build a list of unique subcounty names from PollingStation.
        subcounties_qs = PollingStation.objects.values('subcounty').distinct()
        subcounty_list = [{'id': entry['subcounty'], 'name': entry['subcounty']} for entry in subcounties_qs]
        
        context = {
            'election_positions': election_positions,
            'subcounties': subcounty_list,
        }
        return render(request, "submit_results.html", context)


@login_required
def edit_results_view(request):
    agent = request.user
    # Get polling station id from GET or POST
    polling_station_id = request.GET.get("polling_station_id") if request.method == "GET" else request.POST.get("polling_station")
    if not polling_station_id:
        return HttpResponse("Polling station is required.", status=400)
    try:
        polling_station = PollingStation.objects.get(id=polling_station_id)
    except PollingStation.DoesNotExist:
        return HttpResponse("Invalid polling station.", status=400)

    # Retrieve existing results for this polling station and agent
    results_qs = Result.objects.filter(polling_station=polling_station, agent=agent)
    if not results_qs.exists():
        # If no results exist, redirect to submission form
        return redirect("submit_results")
    
    if request.method == "POST":
        candidate_ids = request.POST.getlist("candidate_ids[]")
        if not candidate_ids:
            return HttpResponse("No candidates found.", status=400)
        for candidate_id in candidate_ids:
            vote_input = request.POST.get(f"votes_{candidate_id}")
            try:
                votes = int(vote_input)
            except (TypeError, ValueError):
                votes = 0
            try:
                candidate = Candidate.objects.get(id=candidate_id)
            except Candidate.DoesNotExist:
                continue
            # Update existing result for this candidate.
            Result.objects.filter(
                polling_station=polling_station,
                candidate=candidate,
                agent=agent
            ).update(votes=votes)
        return redirect("dashboard")
    else:
        # GET: pre-populate the form with existing results.
        candidates_results = []
        for result in results_qs:
            candidates_results.append({
                'candidate_id': result.candidate.id,
                'candidate_name': result.candidate.name,
                'votes': result.votes
            })
        context = {
            'polling_station': polling_station,
            'candidates_results': candidates_results,
        }
        return render(request, "edit_results.html", context)


# AJAX endpoints for dynamic dropdowns
def get_candidates(request):
    position_id = request.GET.get('position_id')
    if not position_id:
        return JsonResponse([], safe=False)
    candidates = Candidate.objects.filter(position__id=position_id)
    data = [{'id': c.id, 'name': c.name} for c in candidates]
    return JsonResponse(data, safe=False)

def get_polling_stations(request):
    # Expecting subcounty name in parameter 'subcounty_id'
    subcounty_name = request.GET.get('subcounty_id')
    if not subcounty_name:
        return JsonResponse([], safe=False)
    stations = PollingStation.objects.filter(subcounty=subcounty_name)
    data = [{'id': s.id, 'name': s.name} for s in stations]
    return JsonResponse(data, safe=False)