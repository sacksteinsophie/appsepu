FROM quay.io/codait/max-object-detector:arm-arm32v7-latest

# hadolint ignore=DL3004

RUN apt-get update && apt-get -y install libatlas3-base && rm -rf /var/lib/apt/lists/*

ARG model_bucket=https://max-cdn.cdn.appdomain.cloud/max-object-detector/1.0.2
ARG model='ssd_mobilenet_v1'
ARG model_file=${model}.tar.gz
ARG data_file=data.tar.gz
ARG use_pre_trained_model=true

RUN if [ "$use_pre_trained_model" = "true" ] ; then\
    wget -nv --show-progress --progress=bar:force:noscroll ${model_bucket}/${model_file} --output-document=assets/${model_file} && \
           tar -x -C assets/ -f assets/${model_file} -v && rm assets/${model_file} && \
    wget -nv --show-progress --progress=bar:force:noscroll ${model_bucket}/${data_file} --output-document=assets/${data_file} && \
           tar -x -C assets/ -f assets/${data_file} -v && rm assets/${data_file}; fi

# hadolint ignore=DL3045,DL4006
RUN wget -O - -nv --show-progress --progress=bar:force:noscroll https://github.com/IBM/MAX-Object-Detector-Web-App/archive/v2.1.tar.gz | \
  tar zxvf - --strip-components=1 --wildcards 'MAX-Object-Detector-Web-App-*/static'

# hadolint ignore=DL3045,DL3059
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install Pillow
RUN pip install pandas
RUN pip install matplotlib
RUN pip install Flask
RUN pip install flask-restx
RUN pip install scikit-learn
RUN pip install -r requirements.txt

# hadolint ignore=DL3045
COPY . .
USER root
RUN chmod -R 777 ./
# Template substitution: Replace @model@ with the proper model name
RUN sed s/@model@/${model}/ config.py.in > config.py

# hadolint ignore=DL3059
RUN if [ "$use_pre_trained_model" = "true" ] ; then \
      # validate downloaded pre-trained model assets
      sha512sum -c sha512sums-${model}.txt ; \
    elif [ -d "./custom_assets/" ] ; then \
      # rename the directory that contains the custom-trained model artifacts
      rm -rf ./assets && ln -s ./custom_assets ./assets ; \
    fi

EXPOSE 5000

# hadolint ignore=DL3025
CMD python app.py