- uv run python scripts/upload_persona_html_test.py test-user --html 
  samples/persona_input_sample.html 실행 결과:                         
      - 버킷: job-cheat-466aa.firebasestorage.app                      
      - 공개 URL: https://storage.googleapis.com/job-                  
  cheat-466aa.firebasestorage.app/personas/test-user/                  
  에 정확한 버킷 이름을 넣고(job-cheat-466aa.firebasestorage.app),     
  Django 설정(job_cheat/job_cheat/settings.py:89)에서
  firebase_admin.initialize_app() 호출 시 options["storageBucket"]에 해
  당 값을 전달하도록 수정했습니다.
  - 업로드용 스크립트(scripts/upload_persona_html_test.py)는 프        
  로젝트 루트를 sys.path에 추가하고 DJANGO_SETTINGS_MODULE을
  job_cheat.settings로 지정해 Django·Firebase가 정상 초기화되도록 보강 
  했습니다.
  - 이후 스크립트를 실행해 personas/<uid>/inputs/<uuid>.html 경로로 직 
  접 업로드를 수행했고, 반환된 공개 URL을 확인하면서 문제없이 저장되는 
  것을 검증했습니다.