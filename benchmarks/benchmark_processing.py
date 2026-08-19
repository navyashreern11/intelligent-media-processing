import statistics
import time
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8000"
IMAGE_PATH = Path("benchmarks/benchmark_image.jpg")
RUNS = 1


def main():
    upload_times = []
    processing_times = []
    successful_runs = 0

    print("=" * 60)
    print("INTELLIGENT MEDIA PROCESSING - PERFORMANCE BENCHMARK")
    print("=" * 60)

    if not IMAGE_PATH.exists():
        print(f"ERROR: Image not found: {IMAGE_PATH}")
        return

    for run in range(1, RUNS + 1):
        print(f"\nRun {run}/{RUNS}")

        # Create a unique copy for each benchmark run.
        # This prevents the duplicate-upload check from rejecting it.
        run_image = IMAGE_PATH.with_name(f"benchmark_image_{run}.jpg")

        data = IMAGE_PATH.read_bytes()
        run_image.write_bytes(data)

        try:
            with httpx.Client(timeout=30.0) as client:

                # Measure upload time
                start_upload = time.perf_counter()

                with open(run_image, "rb") as image:
                    response = client.post(
                        f"{BASE_URL}/api/v1/images/upload",
                        files={
                            "file": (
                                run_image.name,
                                image,
                                "image/jpeg",
                            )
                        },
                    )

                upload_time = time.perf_counter() - start_upload

                if response.status_code != 201:
                    print(
                        f"Upload failed: HTTP {response.status_code}"
                    )
                    print(response.text)
                    continue

                result = response.json()
                processing_id = result["processing_id"]

                upload_times.append(upload_time)

                # Measure asynchronous processing time
                start_processing = time.perf_counter()

                while True:
                    status_response = client.get(
                        f"{BASE_URL}/api/v1/images/"
                        f"{processing_id}/status"
                    )

                    status_response.raise_for_status()

                    status_data = status_response.json()
                    status = status_data.get("status")

                    if status == "completed":
                        processing_time = (
                            time.perf_counter() - start_processing
                        )

                        processing_times.append(processing_time)
                        successful_runs += 1

                        print(f"Processing ID: {processing_id}")
                        print(
                            f"Upload time: "
                            f"{upload_time:.3f} seconds"
                        )
                        print(
                            f"Processing time: "
                            f"{processing_time:.3f} seconds"
                        )

                        break

                    if status == "failed":
                        print("Processing failed.")
                        break

                    time.sleep(0.1)

        except Exception as exc:
            print(f"Benchmark error: {exc}")

        finally:
            if run_image.exists():
                run_image.unlink()

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    if upload_times:
        print(
            f"Average upload time: "
            f"{statistics.mean(upload_times):.3f} seconds"
        )

    if processing_times:
        print(
            f"Average processing time: "
            f"{statistics.mean(processing_times):.3f} seconds"
        )

        print(
            f"Minimum processing time: "
            f"{min(processing_times):.3f} seconds"
        )

        print(
            f"Maximum processing time: "
            f"{max(processing_times):.3f} seconds"
        )

    print(
        f"Successful processing runs: "
        f"{successful_runs}/{RUNS}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()