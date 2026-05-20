FROM nginx:alpine

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制前端静态文件
COPY index.html style.css app.js /usr/share/nginx/html/

EXPOSE 80
