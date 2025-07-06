var express = require('express')
var bodyParser = require('body-parser')
var passport = require('passport')
var session = require('express-session')
var ejs = require('ejs')
var morgan = require('morgan')
const fileUpload = require('express-fileupload');
var config = require('./config/server')

//Initialize Express
var app = express()
require('./core/passport')(passport)
app.use(express.static('public'))
app.set('view engine','ejs')
app.use(morgan('tiny'))
app.use(bodyParser.urlencoded({ extended: false }))
app.use(fileUpload());

// Enable for Reverse proxy support
// app.set('trust proxy', 1) 

// Intialize Session
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


// Routing
app.use('/app',require('./routes/app')())
app.use('/',require('./routes/main')(passport))

// Start Server
app.listen(config.port, config.listen)