from django import forms  
from .models import UserProfile  

from django.contrib.auth.models import User
from allauth.account.forms import SignupForm

class CustomSignupForm(SignupForm):
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("❌ 用户名已被使用，请更换其他用户名")
        return username
    
class ProfileUpdateForm(forms.ModelForm):  
    class Meta:  
        model = UserProfile  
        fields = [ 'bio', 'learning_goal']  
        widgets = {  
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),  
            'learning_goal': forms.TextInput(attrs={'class': 'form-control'}),  
        }  