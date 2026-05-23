import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * @author bedFox
 * @date 2026/4/9 12:30
 */
@SpringBootTest
public class test {
    @Test
    public void testRoom() {
        int ans = 0;
        int year = 2239;
        int mouth = 9;
        int day = 9;
        int endYear = 9876;
        Integer endMouth = 1;
        Integer endDay = 1;

        System.out.println(isCute(2221,1,1));

//        while(year < endYear) {
//            if (isCute(year, mouth, day)) {
//                ans ++;
//            }
//
//        }
    }

    public boolean isCute(Integer year, Integer mouth, Integer day) {
        // 计算当前时间是否可爱
        Integer[] exam = new Integer[10];

        char[] strYear = Integer.toString(year).toCharArray();
        char[] strMouth = Integer.toString(mouth).toCharArray();
        char[] strDay = Integer.toString(day).toCharArray();

        for (char c : strYear) {
            exam[c - '0'] ++;
        }

        for (char c : strMouth) {
            exam[c - '0'] ++;
        }

        for (char c : strDay) {
            exam[c - '0'] ++;
        }

        int res = 0;
        boolean flag = true;
        for (Integer e : exam) {
            if (e == 0)continue;

            if (res == 0) {
                res = e;
            }

            if (res != e) {
                flag = false;
                break;
            }
        }
        return flag;
    }
}
