// Simulated production controller writer.
// The payload is the single-device JSON shape documented by the real HMI.

#include <windows.h>

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

constexpr const char* kSharedMemoryName = "industrial_chamber_realtime_v1";
constexpr std::size_t kSharedMemorySize = 1024 * 256;
constexpr std::size_t kHeaderSize = sizeof(std::uint64_t) + sizeof(std::uint32_t);

struct Header {
    std::uint64_t version;
    std::uint32_t payload_length;
};

std::string now_text() {
    const std::time_t now = std::time(nullptr);
    std::tm local{};
    localtime_s(&local, &now);
    std::ostringstream value;
    value << std::put_time(&local, "%Y-%m-%d %H:%M:%S");
    return value.str();
}

std::string build_snapshot_json(std::uint64_t sequence) {
    const double wave = std::sin(static_cast<double>(sequence) / 12.0);
    const double temperature = -20.0 + wave * 2.2;
    const double humidity = 40.0 + std::cos(static_cast<double>(sequence) / 14.0) * 1.8;
    const bool alarmed = sequence % 70 > 55;
    const char* configured_id = std::getenv("CHAMBER_DEVICE_ID");
    const std::string device_id = configured_id && *configured_id ? configured_id : "SIM-CPP-001";
    const std::string timestamp = now_text();

    std::ostringstream json;
    json << std::fixed << std::setprecision(2);
    json << "{";
    json << "\"DUT\":{";
    for (int index = 0; index < 24; ++index) {
        if (index > 0) json << ",";
        json << "\"DUT" << index << "\":" << (index == 0 ? temperature : 0.0);
    }
    json << ",\"DUT_SEL\":0},";

    json << "\"compressor\":{";
    const char* compressor_keys[] = {
        "A1_Cool", "A1_DP", "A1_DT", "A1_RP", "A2_Cool", "A2_DP", "A2_DT", "A2_RP", "A_Water",
        "B1_Cool", "B1_DP", "B1_DT", "B1_RP", "B2_Cool", "B2_DP", "B2_DT", "B2_RP", "B_Water",
        "C1_Cool", "C1_DP", "C1_DT", "C1_RP", "C2_Cool", "C2_DP", "C2_DT", "C2_RP", "C_Water",
    };
    for (std::size_t index = 0; index < sizeof(compressor_keys) / sizeof(compressor_keys[0]); ++index) {
        if (index > 0) json << ",";
        json << "\"" << compressor_keys[index] << "\":0";
    }
    json << "},";

    json << "\"device_id\":\"" << device_id << "\",";
    json << "\"event\":{";
    for (int index = 0; index < 16; ++index) {
        if (index > 0) json << ",";
        json << "\"event" << index << "\":\"---=OFF\"";
    }
    json << "},";

    json << "\"mainData\":{";
    json << "\"HUMI_Cool\":0,\"HUMI_Hot\":0,\"HUMI_HotG\":0,\"HUMI_HotW\":0,";
    json << "\"HUMI_Out\":" << humidity << ",\"HUMI_PV\":" << humidity << ",\"HUMI_SP\":40.00,";
    json << "\"TEMP_Cool\":0,\"TEMP_Hot\":0,\"TEMP_Out\":" << temperature << ",\"TEMP_PV\":" << temperature << ",\"TEMP_SP\":-20.00,";
    json << "\"pressure_Out\":0,\"pressure_PV\":0,\"pressure_SP\":0,";
    json << "\"runMode\":" << (alarmed ? 0 : 1) << ",\"status\":" << (alarmed ? 2 : 1);
    json << "},\"other\":0,";

    json << "\"program\":{";
    json << "\"download\":\"#1:SIMULATION\",\"fullCycle\":\"0/0\",\"innerLoop\":\"0/0\",";
    json << "\"innerLoopNo\":\"\\u5185\\u90e8\\u5faa\\u73af1\",\"link\":\"#0:---\",";
    json << "\"run\":" << (alarmed ? 0 : 1) << ",\"step\":" << (alarmed ? 0 : 1 + (sequence / 40) % 3);
    json << "},";

    json << "\"status\":{";
    json << "\"alarm\":[" << (alarmed ? "\"\\u8d85\\u6e29\\u4fdd\\u62a4\"" : "") << "],";
    json << "\"state\":\"" << (alarmed ? "\\u8d85\\u6e29\\u4fdd\\u62a4" : "\\u8fd0\\u884c\\u4e2d") << "\"},";
    json << "\"time\":\"" << timestamp << "\",";
    json << "\"timeData\":{";
    json << "\"endTime\":\"\",\"runTime\":\"00:00:00\",\"setTime\":\"00:00:00\",";
    json << "\"startTime\":\"" << timestamp << "\",\"totalTime\":\"00:00:00\"}";
    json << "}";
    return json.str();
}

void write_snapshot(void* memory, const std::string& payload) {
    if (payload.size() > kSharedMemorySize - kHeaderSize) {
        throw std::runtime_error("JSON payload is larger than shared-memory capacity");
    }
    auto* header = reinterpret_cast<Header*>(memory);
    auto* body = reinterpret_cast<char*>(memory) + kHeaderSize;
    std::uint64_t write_version = header->version + 1;
    if (write_version % 2 == 0) ++write_version;
    header->version = write_version;
    header->payload_length = 0;
    std::memcpy(body, payload.data(), payload.size());
    header->payload_length = static_cast<std::uint32_t>(payload.size());
    header->version = write_version + 1;
}

}  // namespace

int main() {
    HANDLE mapping = CreateFileMappingA(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                                        static_cast<DWORD>(kSharedMemorySize), kSharedMemoryName);
    if (!mapping) {
        std::cerr << "CreateFileMapping failed: " << GetLastError() << std::endl;
        return 1;
    }
    void* memory = MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, kSharedMemorySize);
    if (!memory) {
        std::cerr << "MapViewOfFile failed: " << GetLastError() << std::endl;
        CloseHandle(mapping);
        return 1;
    }

    std::cout << "C++ production JSON writer started: " << kSharedMemoryName << std::endl;
    std::uint64_t sequence = 0;
    while (true) {
        const std::string payload = build_snapshot_json(sequence);
        write_snapshot(memory, payload);
        std::cout << "sequence=" << sequence << " payload=" << payload.size() << " bytes" << std::endl;
        ++sequence;
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
}
