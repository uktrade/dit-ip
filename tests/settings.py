SECRET_KEY = 'fake-key'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'tests'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ROOT_URLCONF = 'tests.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

import django
# Django changed the settings variable for middleware between 1.9 and 1.10
# Set the correct variable needed for testing based on the installed django version
version_components = [int(comp) for comp in django.get_version().split('.')]

# Basic necessary middleware for the IpWhitelister to work
_middleware = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'ip_restriction.IpWhitelister'
]

if version_components[0] == 1 and version_components[1] == 9:
    MIDDLEWARE_CLASSES = _middleware
elif version_components[0] == 1 and version_components[1] >= 10:
    MIDDLEWARE = _middleware
elif version_components[0] == 2:
    MIDDLEWARE = _middleware
