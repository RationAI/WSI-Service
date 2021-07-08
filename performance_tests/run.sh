DATA=/cache/staff/weiss/wsi-service-data/OpenSlide_adapted
WEB_CONCURRENCY=16
GIT_HASH=$(git rev-parse --short HEAD)
docker network create wsi-test-network
docker run --network=wsi-test-network -e WEB_CONCURRENCY=$WEB_CONCURRENCY --rm -v $DATA:/data --name=wsi-service -d registry.gitlab.com/empaia/services/wsi-service
docker build . -t wsi-service-performance-tests
docker run --network=wsi-test-network -e WEB_CONCURRENCY=$WEB_CONCURRENCY -e GIT_HASH=$GIT_HASH -e WSI_SERVICE_ADDRESS="http://wsi-service:8080" --rm -v $(pwd):/scripts/ wsi-service-performance-tests python3 /scripts/run_performance_tests_wsi_service.py
docker kill wsi-service
docker network rm wsi-test-network
docker run --rm -v $DATA:/data -e GIT_HASH=$GIT_HASH -v $(pwd):/scripts/ wsi-service-performance-tests python3 /scripts/run_performance_tests_openslide.py