app.use(session({
     secret: process.env.SESSION_SECRET || 'defaultSecret', // 환경 변수를 사용하여 secret 설정
     resave: false, // 필요에 따라 false로 설정하여 성능 최적화
     saveUninitialized: false, // 필요에 따라 false로 설정하여 성능 최적화
     cookie: {
       secure: process.env.NODE_ENV === 'production', // 프로덕션 환경에서는 true로 설정
       httpOnly: true, // 클라이언트 측에서 쿠키 접근 방지
       domain: 'yourdomain.com', // 필요에 따라 설정
       expires: new Date(Date.now() + 60 * 60 * 1000), // 1시간 후 만료
       path: '/' // 필요에 따라 설정
     }
   }))

