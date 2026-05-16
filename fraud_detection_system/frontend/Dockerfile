FROM node:18-alpine

WORKDIR /app

COPY package.json ./

# Assuming simple npm install for vite project
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
