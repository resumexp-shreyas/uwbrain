from django.urls import path

from . import views

# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import CustomSectionViewSet, CustomSectionItemViewSet

# router = DefaultRouter()
# router.register(r'customsections', CustomSectionViewSet)
# router.register(r'customsectionitems', CustomSectionItemViewSet)

##############################################################
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProposalViewSet, AmbiguityViewSet, DiscrepancyViewSet

router = DefaultRouter()
router.register(r'proposals', ProposalViewSet)
router.register(r'ambiguities', AmbiguityViewSet)
router.register(r'discrepancies', DiscrepancyViewSet)
##############################################################

app_name = 'proposal'
urlpatterns = [
    path('submit/', views.submit.as_view(), name='submit'),
    path('getclarity/', views.getclarity.as_view(), name='getclarity'),
    path('findambiguity/', views.findambiguity.as_view(), name='findambiguity'),
    path('SubmitAdditionalAnswers/', views.SubmitAdditionalAnswers.as_view(), name='SubmitAdditionalAnswers'),
    path('postUWQn/', views.postUWQn.as_view(), name='postUWQn'),
    # path('CreateResume/', views.CreateResume.as_view(), name='CreateResume'),
    # path('getResumeList/', views.getResumeList.as_view(), name='getResumeList'),
    # path('CreatewithAI/', views.CreatewithAI.as_view(), name='CreatewithAI'),
    path('api/', include(router.urls)),
    
]